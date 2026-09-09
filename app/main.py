import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.routers import (
    analytics,
    clientes,
    configuracoes,
    dashboard,
    estoque,
    financeiro,
    ingredientes,
    produtos,
    receitas,
    relatorios,
    vendas,
)

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("erp")

STATIC_DIR = Path(__file__).resolve().parent.parent / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM vw_dashboard_kpis"))
        logger.info("Banco conectado - ERP pronto em http://localhost:%s", settings.port)
    except Exception as exc:
        logger.error(
            "Nao foi possivel usar o banco (%s). Rode schema.sql, views.sql e seeds.sql "
            "e confira o DATABASE_URL do .env",
            exc,
        )
    yield
    await engine.dispose()


app = FastAPI(
    title=f"ERP {settings.empresa_nome}",
    description="Gestao de receitas, custos, estoque, vendas e financeiro da confeitaria.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for modulo in (
    dashboard,
    analytics,
    ingredientes,
    receitas,
    produtos,
    clientes,
    vendas,
    estoque,
    financeiro,
    relatorios,
    configuracoes,
):
    app.include_router(modulo.router)


@app.get("/api/health", tags=["Sistema"])
async def health():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "banco": "conectado", "empresa": settings.empresa_nome}
    except Exception as exc:
        return JSONResponse(
            status_code=503, content={"status": "erro", "banco": "indisponivel", "detalhe": str(exc)}
        )


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
