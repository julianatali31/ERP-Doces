from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import TransacaoFinanceira
from app.schemas import TransacaoCreate, TransacaoOut, TransacaoUpdate

router = APIRouter(prefix="/api/financeiro", tags=["Financeiro"])


@router.get("/transacoes", response_model=list[TransacaoOut])
async def listar(
    inicio: date | None = None,
    fim: date | None = None,
    tipo: str | None = None,
    categoria: str | None = None,
    limite: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TransacaoFinanceira)
        .order_by(TransacaoFinanceira.data_transacao.desc(), TransacaoFinanceira.id.desc())
        .limit(limite)
    )
    if inicio:
        stmt = stmt.where(TransacaoFinanceira.data_transacao >= inicio)
    if fim:
        stmt = stmt.where(TransacaoFinanceira.data_transacao <= fim)
    if tipo:
        stmt = stmt.where(TransacaoFinanceira.tipo == tipo)
    if categoria:
        stmt = stmt.where(TransacaoFinanceira.categoria == categoria)
    return (await db.execute(stmt)).scalars().all()


@router.get("/resumo")
async def resumo(
    inicio: date | None = None,
    fim: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    filtros = [TransacaoFinanceira.status == "pago"]
    if inicio:
        filtros.append(TransacaoFinanceira.data_transacao >= inicio)
    if fim:
        filtros.append(TransacaoFinanceira.data_transacao <= fim)

    stmt = select(
        func.coalesce(
            func.sum(TransacaoFinanceira.valor).filter(TransacaoFinanceira.tipo == "receita"), 0
        ),
        func.coalesce(
            func.sum(TransacaoFinanceira.valor).filter(TransacaoFinanceira.tipo == "despesa"), 0
        ),
    ).where(*filtros)

    receitas, despesas = (await db.execute(stmt)).one()

    por_categoria = (
        await db.execute(
            select(
                TransacaoFinanceira.tipo,
                TransacaoFinanceira.categoria,
                func.sum(TransacaoFinanceira.valor),
            )
            .where(*filtros)
            .group_by(TransacaoFinanceira.tipo, TransacaoFinanceira.categoria)
            .order_by(func.sum(TransacaoFinanceira.valor).desc())
        )
    ).all()

    return {
        "receitas": float(receitas),
        "despesas": float(despesas),
        "saldo": float(receitas) - float(despesas),
        "por_categoria": [
            {"tipo": t, "categoria": c, "total": float(v)} for t, c, v in por_categoria
        ],
    }


@router.post("/transacoes", response_model=TransacaoOut, status_code=201)
async def criar(dados: TransacaoCreate, db: AsyncSession = Depends(get_db)):
    campos = dados.model_dump()
    if campos.get("data_transacao") is None:
        campos["data_transacao"] = date.today()
    transacao = TransacaoFinanceira(**campos)
    db.add(transacao)
    await db.commit()
    await db.refresh(transacao)
    return transacao


@router.put("/transacoes/{transacao_id}", response_model=TransacaoOut)
async def atualizar(
    transacao_id: int, dados: TransacaoUpdate, db: AsyncSession = Depends(get_db)
):
    transacao = await db.get(TransacaoFinanceira, transacao_id)
    if not transacao:
        raise HTTPException(404, "Transacao nao encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(transacao, campo, valor)
    await db.commit()
    await db.refresh(transacao)
    return transacao


@router.delete("/transacoes/{transacao_id}", status_code=204)
async def remover(transacao_id: int, db: AsyncSession = Depends(get_db)):
    transacao = await db.get(TransacaoFinanceira, transacao_id)
    if not transacao:
        raise HTTPException(404, "Transacao nao encontrada")
    await db.delete(transacao)
    await db.commit()
