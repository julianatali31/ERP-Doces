from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Produto, Receita, VendaItem
from app.schemas import PrecoSugerido, ProdutoCreate, ProdutoOut, ProdutoUpdate

router = APIRouter(prefix="/api/produtos", tags=["Produtos"])


def _saida(produto: Produto) -> ProdutoOut:
    out = ProdutoOut.model_validate(produto)
    out.receita_nome = produto.receita.nome if produto.receita else None
    return out


@router.get("", response_model=list[ProdutoOut])
async def listar(
    busca: str | None = None,
    categoria: str | None = None,
    apenas_ativos: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Produto).order_by(Produto.nome)
    if apenas_ativos:
        stmt = stmt.where(Produto.ativo.is_(True))
    if categoria:
        stmt = stmt.where(Produto.categoria == categoria)
    if busca:
        stmt = stmt.where(func.lower(Produto.nome).like(f"%{busca.lower()}%"))
    return [_saida(p) for p in (await db.execute(stmt)).unique().scalars().all()]


@router.get("/{produto_id}", response_model=ProdutoOut)
async def obter(produto_id: int, db: AsyncSession = Depends(get_db)):
    produto = await db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(404, "Produto nao encontrado")
    return _saida(produto)


@router.get("/{produto_id}/preco-sugerido", response_model=PrecoSugerido)
async def preco_sugerido(
    produto_id: int,
    margem: float = Query(60, ge=0, lt=100, description="Margem de lucro desejada em %"),
    db: AsyncSession = Depends(get_db),
):
    """Preco que entrega a margem pedida sobre o preco de venda (markup divisor)."""
    produto = await db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(404, "Produto nao encontrado")

    custo = float(produto.custo_unitario)
    sugerido = round(custo / (1 - margem / 100), 2) if custo > 0 else 0.0
    return PrecoSugerido(
        produto=produto.nome,
        custo_unitario=custo,
        margem_desejada=margem,
        preco_sugerido=sugerido,
        preco_atual=float(produto.preco_venda),
    )


@router.post("", response_model=ProdutoOut, status_code=201)
async def criar(dados: ProdutoCreate, db: AsyncSession = Depends(get_db)):
    if dados.receita_id and not await db.get(Receita, dados.receita_id):
        raise HTTPException(404, "Receita vinculada nao encontrada")

    produto = Produto(**dados.model_dump())
    db.add(produto)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"Ja existe um produto chamado '{dados.nome}'")
    await db.refresh(produto)
    return _saida(produto)


@router.put("/{produto_id}", response_model=ProdutoOut)
async def atualizar(produto_id: int, dados: ProdutoUpdate, db: AsyncSession = Depends(get_db)):
    produto = await db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(404, "Produto nao encontrado")

    campos = dados.model_dump(exclude_unset=True)
    if campos.get("receita_id") and not await db.get(Receita, campos["receita_id"]):
        raise HTTPException(404, "Receita vinculada nao encontrada")

    for campo, valor in campos.items():
        setattr(produto, campo, valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Ja existe outro produto com esse nome")
    await db.refresh(produto)
    return _saida(produto)


@router.delete("/{produto_id}", status_code=204)
async def remover(produto_id: int, db: AsyncSession = Depends(get_db)):
    produto = await db.get(Produto, produto_id)
    if not produto:
        raise HTTPException(404, "Produto nao encontrado")

    vendido = await db.scalar(
        select(func.count(VendaItem.id)).where(VendaItem.produto_id == produto_id)
    )
    if vendido:
        produto.ativo = False
        await db.commit()
        return

    await db.delete(produto)
    await db.commit()
