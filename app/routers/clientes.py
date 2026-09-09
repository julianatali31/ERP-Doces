from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Cliente, Venda
from app.schemas import ClienteCreate, ClienteOut, ClienteUpdate

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


@router.get("", response_model=list[ClienteOut])
async def listar(
    busca: str | None = None,
    apenas_ativos: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Cliente).order_by(Cliente.nome)
    if apenas_ativos:
        stmt = stmt.where(Cliente.ativo.is_(True))
    if busca:
        termo = f"%{busca.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Cliente.nome).like(termo),
                func.lower(func.coalesce(Cliente.email, "")).like(termo),
                func.coalesce(Cliente.telefone, "").like(termo),
            )
        )
    return (await db.execute(stmt)).scalars().all()


@router.get("/{cliente_id}", response_model=ClienteOut)
async def obter(cliente_id: int, db: AsyncSession = Depends(get_db)):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente nao encontrado")
    return cliente


@router.post("", response_model=ClienteOut, status_code=201)
async def criar(dados: ClienteCreate, db: AsyncSession = Depends(get_db)):
    cliente = Cliente(**dados.model_dump())
    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.put("/{cliente_id}", response_model=ClienteOut)
async def atualizar(cliente_id: int, dados: ClienteUpdate, db: AsyncSession = Depends(get_db)):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente nao encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cliente, campo, valor)
    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}", status_code=204)
async def remover(
    cliente_id: int,
    forcar: bool = Query(False, description="Apaga mesmo tendo vendas (as vendas ficam sem cliente)"),
    db: AsyncSession = Depends(get_db),
):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(404, "Cliente nao encontrado")

    tem_venda = await db.scalar(select(func.count(Venda.id)).where(Venda.cliente_id == cliente_id))
    if tem_venda and not forcar:
        cliente.ativo = False
        await db.commit()
        return

    await db.delete(cliente)
    await db.commit()
