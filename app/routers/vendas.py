from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.tempo import local
from app.models import Cliente, Produto, TransacaoFinanceira, Venda, VendaItem
from app.schemas import VendaCreate, VendaItemOut, VendaOut
from app.services import consumir_receita

router = APIRouter(prefix="/api/vendas", tags=["Vendas"])

# Ordenacoes aceitas na listagem. Lista fechada: o valor vem da URL e vira
# ORDER BY, entao nada fora daqui chega ao SQL.
_ORDENACOES = {
    "recentes": Venda.data_venda.desc(),
    "antigas": Venda.data_venda.asc(),
    "maior_total": Venda.total.desc(),
    "menor_total": Venda.total.asc(),
    "maior_lucro": Venda.lucro.desc(),
    "menor_lucro": Venda.lucro.asc(),
}


def _saida(venda: Venda) -> VendaOut:
    out = VendaOut.model_validate(venda)
    out.cliente_nome = venda.cliente.nome if venda.cliente else None
    out.itens = [VendaItemOut.model_validate(i) for i in venda.itens]
    return out


async def _carregar(db: AsyncSession, venda_id: int) -> Venda:
    venda = (
        await db.execute(select(Venda).where(Venda.id == venda_id))
    ).unique().scalar_one_or_none()
    if not venda:
        raise HTTPException(404, "Venda nao encontrada")
    return venda


@router.get("", response_model=list[VendaOut])
async def listar(
    inicio: date | None = None,
    fim: date | None = None,
    cliente_id: int | None = None,
    status: str | None = None,
    forma_pagamento: str | None = None,
    prejuizo: bool = Query(False, description="So vendas com lucro negativo"),
    ordem: str = Query("recentes", pattern="^(" + "|".join(_ORDENACOES) + ")$"),
    limite: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    # id desempata vendas com o mesmo valor, para a ordem nao mudar a cada carga
    stmt = select(Venda).order_by(_ORDENACOES[ordem], Venda.id.desc()).limit(limite)
    if inicio:
        stmt = stmt.where(func.date(Venda.data_venda) >= inicio)
    if fim:
        stmt = stmt.where(func.date(Venda.data_venda) <= fim)
    if cliente_id:
        stmt = stmt.where(Venda.cliente_id == cliente_id)
    if status:
        stmt = stmt.where(Venda.status == status)
    if forma_pagamento:
        stmt = stmt.where(Venda.forma_pagamento == forma_pagamento)
    if prejuizo:
        stmt = stmt.where(Venda.lucro < 0)
    vendas = (await db.execute(stmt)).unique().scalars().all()
    return [_saida(v) for v in vendas]


@router.get("/{venda_id}", response_model=VendaOut)
async def obter(venda_id: int, db: AsyncSession = Depends(get_db)):
    return _saida(await _carregar(db, venda_id))


@router.post("", response_model=VendaOut, status_code=201)
async def criar(dados: VendaCreate, db: AsyncSession = Depends(get_db)):
    if dados.cliente_id and not await db.get(Cliente, dados.cliente_id):
        raise HTTPException(404, "Cliente nao encontrado")

    venda = Venda(
        cliente_id=dados.cliente_id,
        desconto=Decimal(str(dados.desconto)),
        forma_pagamento=dados.forma_pagamento,
        status=dados.status,
        observacoes=dados.observacoes,
    )
    if dados.data_venda:
        venda.data_venda = dados.data_venda
    db.add(venda)
    await db.flush()

    baixas: list[tuple[int, Decimal]] = []
    subtotal = Decimal(0)
    for item in dados.itens:
        produto = None
        if item.produto_id:
