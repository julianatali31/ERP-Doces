from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Configuracao
from app.schemas import ConfiguracaoOut, ConfiguracaoUpdate

router = APIRouter(prefix="/api/configuracoes", tags=["Configuracoes"])


@router.get("", response_model=list[ConfiguracaoOut])
async def listar(grupo: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Configuracao).order_by(Configuracao.grupo, Configuracao.chave)
    if grupo:
        stmt = stmt.where(Configuracao.grupo == grupo)
    return (await db.execute(stmt)).scalars().all()


@router.put("/{chave}", response_model=ConfiguracaoOut)
async def atualizar(chave: str, dados: ConfiguracaoUpdate, db: AsyncSession = Depends(get_db)):
    config = (
        await db.execute(select(Configuracao).where(Configuracao.chave == chave))
    ).scalar_one_or_none()
    if not config:
        raise HTTPException(404, f"Configuracao '{chave}' nao encontrada")
    config.valor = dados.valor
    await db.commit()
    await db.refresh(config)
    return config
