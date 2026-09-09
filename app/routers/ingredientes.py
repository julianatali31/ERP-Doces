from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Ingrediente, ReceitaIngrediente
from app.schemas import (
    IngredienteCreate,
    IngredienteOut,
    IngredientePrecoCompra,
    IngredienteUpdate,
)
from app.services import converter_unidade, registrar_movimentacao

router = APIRouter(prefix="/api/ingredientes", tags=["Ingredientes"])


@router.get("", response_model=list[IngredienteOut])
async def listar(
    busca: str | None = None,
    categoria: str | None = None,
    apenas_ativos: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Ingrediente).order_by(Ingrediente.nome)
    if apenas_ativos:
        stmt = stmt.where(Ingrediente.ativo.is_(True))
    if categoria:
        stmt = stmt.where(Ingrediente.categoria == categoria)
    if busca:
        stmt = stmt.where(func.lower(Ingrediente.nome).like(f"%{busca.lower()}%"))
    return (await db.execute(stmt)).scalars().all()


@router.get("/categorias", response_model=list[str])
async def listar_categorias(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Ingrediente.categoria)
        .where(Ingrediente.categoria.is_not(None))
        .distinct()
        .order_by(Ingrediente.categoria)
    )
    return [c for c in (await db.execute(stmt)).scalars().all()]


@router.get("/{ingrediente_id}", response_model=IngredienteOut)
async def obter(ingrediente_id: int, db: AsyncSession = Depends(get_db)):
    ingrediente = await db.get(Ingrediente, ingrediente_id)
    if not ingrediente:
        raise HTTPException(404, "Ingrediente nao encontrado")
    return ingrediente


@router.post("", response_model=IngredienteOut, status_code=201)
async def criar(dados: IngredienteCreate, db: AsyncSession = Depends(get_db)):
    ingrediente = Ingrediente(**dados.model_dump())
    db.add(ingrediente)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"Ja existe um ingrediente chamado '{dados.nome}'")
    await db.refresh(ingrediente)
    return ingrediente


@router.put("/{ingrediente_id}", response_model=IngredienteOut)
async def atualizar(
    ingrediente_id: int, dados: IngredienteUpdate, db: AsyncSession = Depends(get_db)
):
    ingrediente = await db.get(Ingrediente, ingrediente_id)
    if not ingrediente:
        raise HTTPException(404, "Ingrediente nao encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(ingrediente, campo, valor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Ja existe outro ingrediente com esse nome")
    await db.refresh(ingrediente)
    return ingrediente


@router.post("/{ingrediente_id}/preco-compra", response_model=IngredienteOut)
async def registrar_preco_compra(
    ingrediente_id: int, dados: IngredientePrecoCompra, db: AsyncSession = Depends(get_db)
):
    """Recalcula o custo unitario a partir do preco de uma embalagem.

    Ex.: R$ 20,00 num pacote de 5 kg de farinha cadastrada em 'g' -> R$ 0,004/g.
    """
    ingrediente = await db.get(Ingrediente, ingrediente_id)
    if not ingrediente:
        raise HTTPException(404, "Ingrediente nao encontrado")

    qtd_base = converter_unidade(
        Decimal(str(dados.quantidade_embalagem)),
        dados.unidade_embalagem,
        ingrediente.unidade_medida,
    )
    if qtd_base <= 0:
        raise HTTPException(400, "Quantidade da embalagem invalida")

    novo_custo = Decimal(str(dados.preco_pago)) / qtd_base

    if dados.lancar_entrada:
        await registrar_movimentacao(
            db,
            ingrediente,
            "entrada",
            qtd_base,
            custo_unitario=novo_custo,
            motivo=f"Compra: R$ {dados.preco_pago:.2f} por "
            f"{dados.quantidade_embalagem:g} {dados.unidade_embalagem}",
        )
    else:
        ingrediente.custo_unitario = novo_custo

    await db.commit()
    await db.refresh(ingrediente)
    return ingrediente


@router.delete("/{ingrediente_id}", status_code=204)
async def remover(ingrediente_id: int, db: AsyncSession = Depends(get_db)):
    ingrediente = await db.get(Ingrediente, ingrediente_id)
    if not ingrediente:
        raise HTTPException(404, "Ingrediente nao encontrado")

    usos = await db.scalar(
        select(func.count(ReceitaIngrediente.id)).where(
            ReceitaIngrediente.ingrediente_id == ingrediente_id
        )
    )
    if usos:
        ingrediente.ativo = False
        await db.commit()
        return

    await db.delete(ingrediente)
    await db.commit()
