from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Ingrediente, MovimentacaoEstoque
from app.schemas import EstoqueOut, MovimentacaoIn, MovimentacaoOut
from app.services import registrar_movimentacao

router = APIRouter(prefix="/api/estoque", tags=["Estoque"])


@router.get("", response_model=list[EstoqueOut])
async def situacao(
    situacao: str | None = Query(None, description="ok | atencao | baixo | sem_estoque"),
    db: AsyncSession = Depends(get_db),
):
    sql = "SELECT * FROM vw_estoque WHERE ativo"
    params: dict = {}
    if situacao:
        sql += " AND situacao = :situacao"
        params["situacao"] = situacao
    sql += " ORDER BY nome"

    linhas = (await db.execute(text(sql), params)).mappings().all()
    return [EstoqueOut(**linha) for linha in linhas]


@router.get("/alertas", response_model=list[EstoqueOut])
async def alertas(db: AsyncSession = Depends(get_db)):
    linhas = (await db.execute(text("SELECT * FROM vw_estoque_baixo"))).mappings().all()
    return [EstoqueOut(**linha) for linha in linhas]


@router.get("/movimentacoes", response_model=list[MovimentacaoOut])
async def movimentacoes(
    ingrediente_id: int | None = None,
    tipo: str | None = None,
    limite: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(MovimentacaoEstoque)
        .order_by(MovimentacaoEstoque.criado_em.desc(), MovimentacaoEstoque.id.desc())
        .limit(limite)
    )
    if ingrediente_id:
        stmt = stmt.where(MovimentacaoEstoque.ingrediente_id == ingrediente_id)
    if tipo:
        stmt = stmt.where(MovimentacaoEstoque.tipo == tipo)

    movimentos = (await db.execute(stmt)).unique().scalars().all()
    saida = []
    for m in movimentos:
        item = MovimentacaoOut.model_validate(m)
        item.ingrediente_nome = m.ingrediente.nome if m.ingrediente else None
        saida.append(item)
    return saida


@router.post("/movimentacoes", response_model=MovimentacaoOut, status_code=201)
async def movimentar(dados: MovimentacaoIn, db: AsyncSession = Depends(get_db)):
    ingrediente = await db.get(Ingrediente, dados.ingrediente_id)
    if not ingrediente:
        raise HTTPException(404, "Ingrediente nao encontrado")

    mov = await registrar_movimentacao(
        db,
        ingrediente,
        dados.tipo,
        Decimal(str(dados.quantidade)),
        custo_unitario=Decimal(str(dados.custo_unitario)) if dados.custo_unitario is not None else None,
        motivo=dados.motivo,
        referencia=dados.referencia,
    )
    await db.commit()
    await db.refresh(mov)

    saida = MovimentacaoOut.model_validate(mov)
    saida.ingrediente_nome = ingrediente.nome
    return saida
