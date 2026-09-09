from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DashboardKpis, SerieTemporal

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/kpis", response_model=DashboardKpis)
async def kpis(db: AsyncSession = Depends(get_db)):
    linha = (await db.execute(text("SELECT * FROM vw_dashboard_kpis"))).mappings().one()
    dados = {k: float(v) for k, v in linha.items()}
    dados["vendas_mes"] = int(dados["vendas_mes"])
    dados["itens_estoque_baixo"] = int(dados["itens_estoque_baixo"])
    dados["total_produtos"] = int(dados["total_produtos"])
    dados["total_receitas"] = int(dados["total_receitas"])
    dados["total_clientes"] = int(dados["total_clientes"])
    dados["saldo_mes"] = dados["faturamento_mes"] - dados["despesas_mes"]
    return DashboardKpis(**dados)


@router.get("/vendas-por-dia", response_model=list[SerieTemporal])
async def vendas_por_dia(dias: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db)):
    """Faturamento e lucro por dia, incluindo dias sem venda."""
    linhas = (
        await db.execute(
            text(
                """
                SELECT d::date AS dia,
                       COALESCE(v.faturamento, 0) AS faturamento,
                       COALESCE(v.lucro, 0)       AS lucro
                FROM generate_series(:inicio, CURRENT_DATE, INTERVAL '1 day') d
                LEFT JOIN vw_vendas_por_dia v ON v.dia = d::date
                ORDER BY d
                """
            ),
            {"inicio": date.today() - timedelta(days=dias - 1)},
        )
    ).mappings().all()

    return [
        SerieTemporal(
            label=linha["dia"].strftime("%d/%m"),
            valor=float(linha["faturamento"]),
            valor_secundario=float(linha["lucro"]),
        )
        for linha in linhas
    ]


@router.get("/produtos-mais-vendidos", response_model=list[SerieTemporal])
async def produtos_mais_vendidos(
    limite: int = Query(8, ge=1, le=50), db: AsyncSession = Depends(get_db)
):
    linhas = (
        await db.execute(
            text("SELECT produto, unidades_vendidas, faturamento FROM vw_produtos_mais_vendidos LIMIT :limite"),
            {"limite": limite},
        )
    ).mappings().all()

    return [
        SerieTemporal(
            label=linha["produto"],
            valor=float(linha["unidades_vendidas"]),
            valor_secundario=float(linha["faturamento"]),
        )
        for linha in linhas
    ]


@router.get("/margem-produtos")
async def margem_produtos(db: AsyncSession = Depends(get_db)):
    linhas = (
        await db.execute(
            text(
                """
                SELECT nome, preco_venda, custo_unitario, margem_valor,
                       margem_lucro, classificacao_margem
                FROM vw_produtos_margem
                WHERE ativo
                ORDER BY margem_lucro ASC
                """
            )
        )
    ).mappings().all()
    return [{k: (float(v) if isinstance(v, (int, float)) or hasattr(v, "quantize") else v)
             for k, v in linha.items()} for linha in linhas]


@router.get("/fluxo-caixa", response_model=list[SerieTemporal])
async def fluxo_caixa(meses: int = Query(6, ge=1, le=36), db: AsyncSession = Depends(get_db)):
    hoje = date.today()
    total_meses = hoje.year * 12 + hoje.month - 1 - (meses - 1)
    primeiro_mes = date(total_meses // 12, total_meses % 12 + 1, 1)

    linhas = (
        await db.execute(
            text(
                """
                SELECT m::date AS mes,
                       COALESCE(f.receitas, 0) AS receitas,
                       COALESCE(f.despesas, 0) AS despesas
                FROM generate_series(
                        :inicio, DATE_TRUNC('month', CURRENT_DATE), INTERVAL '1 month'
                     ) m
                LEFT JOIN vw_fluxo_caixa_mensal f ON f.mes = m::date
                ORDER BY m
                """
            ),
            {"inicio": primeiro_mes},
        )
    ).mappings().all()

    return [
        SerieTemporal(
            label=linha["mes"].strftime("%m/%Y"),
            valor=float(linha["receitas"]),
            valor_secundario=float(linha["despesas"]),
        )
        for linha in linhas
    ]
