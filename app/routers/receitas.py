from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Ingrediente, Receita, ReceitaIngrediente
from app.schemas import (
    ProducaoIn,
    ProducaoOut,
    ReceitaCreate,
    ReceitaDetalhe,
    ReceitaIngredienteOut,
    ReceitaOut,
    ReceitaUpdate,
)
from app.services import consumir_receita, converter_unidade

router = APIRouter(prefix="/api/receitas", tags=["Receitas"])


async def _montar_detalhe(db: AsyncSession, receita: Receita) -> ReceitaDetalhe:
    linhas = (
        await db.execute(
            select(ReceitaIngrediente, Ingrediente)
            .join(Ingrediente, Ingrediente.id == ReceitaIngrediente.ingrediente_id)
            .where(ReceitaIngrediente.receita_id == receita.id)
            .order_by(Ingrediente.nome)
        )
    ).all()

    detalhe = ReceitaDetalhe.model_validate(receita)
    detalhe.ingredientes = [
        ReceitaIngredienteOut(
            id=item.id,
            ingrediente_id=item.ingrediente_id,
            quantidade=float(item.quantidade),
            unidade=item.unidade,
            observacao=item.observacao,
            ingrediente_nome=ing.nome,
            custo_linha=float(
                converter_unidade(Decimal(item.quantidade), item.unidade, ing.unidade_medida)
                * Decimal(ing.custo_unitario)
            ),
        )
        for item, ing in linhas
    ]
    return detalhe


async def _gravar_ingredientes(db: AsyncSession, receita_id: int, itens) -> None:
    await db.execute(
        delete(ReceitaIngrediente).where(ReceitaIngrediente.receita_id == receita_id)
    )
    vistos: set[int] = set()
    for item in itens:
        if item.ingrediente_id in vistos:
            raise HTTPException(400, "O mesmo ingrediente foi informado duas vezes na receita")
        vistos.add(item.ingrediente_id)
        if not await db.get(Ingrediente, item.ingrediente_id):
            raise HTTPException(404, f"Ingrediente {item.ingrediente_id} nao encontrado")
        db.add(
            ReceitaIngrediente(
                receita_id=receita_id,
                ingrediente_id=item.ingrediente_id,
                quantidade=Decimal(str(item.quantidade)),
                unidade=item.unidade,
                observacao=item.observacao,
            )
        )
    await db.flush()


@router.get("", response_model=list[ReceitaOut])
async def listar(
    busca: str | None = None,
    categoria: str | None = None,
    apenas_ativas: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Receita).order_by(Receita.nome)
    if apenas_ativas:
        stmt = stmt.where(Receita.ativo.is_(True))
    if categoria:
        stmt = stmt.where(Receita.categoria == categoria)
    if busca:
        stmt = stmt.where(func.lower(Receita.nome).like(f"%{busca.lower()}%"))
    return (await db.execute(stmt)).scalars().all()


@router.get("/{receita_id}", response_model=ReceitaDetalhe)
async def obter(receita_id: int, db: AsyncSession = Depends(get_db)):
    receita = await db.get(Receita, receita_id)
    if not receita:
        raise HTTPException(404, "Receita nao encontrada")
    return await _montar_detalhe(db, receita)


@router.post("", response_model=ReceitaDetalhe, status_code=201)
async def criar(dados: ReceitaCreate, db: AsyncSession = Depends(get_db)):
    payload = dados.model_dump(exclude={"ingredientes"})
    receita = Receita(**payload)
    db.add(receita)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"Ja existe uma receita chamada '{dados.nome}'")

    await _gravar_ingredientes(db, receita.id, dados.ingredientes)
    await db.commit()
    await db.refresh(receita)
    return await _montar_detalhe(db, receita)


@router.put("/{receita_id}", response_model=ReceitaDetalhe)
async def atualizar(receita_id: int, dados: ReceitaUpdate, db: AsyncSession = Depends(get_db)):
    receita = await db.get(Receita, receita_id)
    if not receita:
        raise HTTPException(404, "Receita nao encontrada")

    campos = dados.model_dump(exclude_unset=True, exclude={"ingredientes"})
    for campo, valor in campos.items():
        setattr(receita, campo, valor)

    if dados.ingredientes is not None:
        await _gravar_ingredientes(db, receita_id, dados.ingredientes)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Ja existe outra receita com esse nome")

    await db.refresh(receita)
    return await _montar_detalhe(db, receita)


@router.post("/{receita_id}/produzir", response_model=ProducaoOut)
async def produzir(receita_id: int, dados: ProducaoIn, db: AsyncSession = Depends(get_db)):
    """Da baixa nos insumos de uma producao (fornada) e registra no kardex."""
    receita = await db.get(Receita, receita_id)
    if not receita:
        raise HTTPException(404, "Receita nao encontrada")

    fator = Decimal(str(dados.lotes))
    consumidos = await consumir_receita(
        db,
        receita_id,
        fator,
        motivo=dados.observacao or f"Producao de {dados.lotes:g}x {receita.nome}",
        referencia=f"producao:{receita_id}",
    )
    if not consumidos:
        raise HTTPException(400, "A receita nao tem ingredientes cadastrados")

    await db.commit()
    return ProducaoOut(
        receita=receita.nome,
        lotes=dados.lotes,
        unidades_produzidas=float(Decimal(receita.rendimento) * fator),
        custo_total=float(Decimal(receita.custo_total) * fator),
        ingredientes_consumidos=consumidos,
    )


@router.delete("/{receita_id}", status_code=204)
async def remover(receita_id: int, db: AsyncSession = Depends(get_db)):
    receita = await db.get(Receita, receita_id)
    if not receita:
        raise HTTPException(404, "Receita nao encontrada")
    await db.delete(receita)
    await db.commit()
