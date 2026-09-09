"""Camada de leitura agregada das vendas.

Só consulta: nenhum endpoint aqui grava, atualiza ou apaga. As métricas que o
módulo Dashboard já entrega (faturamento por dia, KPIs do mês) não são
reimplementadas — a tela de analytics consome os endpoints existentes para
essas e usa as rotas abaixo para o que ainda não havia: agrupamento por semana
e mês, comparação com o período anterior, ranking por período e sazonalidade.
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ComparativoPeriodo,
    IndicadorComparado,
    MesSazonalidade,
    PontoFaturamento,
    ProdutoRanking,
)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

MESES = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)

# Quais meses marcar como recesso vem da tabela de configurações, para o
# calendário poder mudar sem alterar código.
CHAVE_RECESSO = "meses_recesso"

# granularidade aceita -> (unidade do DATE_TRUNC, passo do generate_series)
GRANULARIDADES = {"semana": ("week", "1 week"), "mes": ("month", "1 month")}


def _periodo_padrao(inicio: date | None, fim: date | None) -> tuple[date, date]:
    """Sem datas informadas, usa os últimos 30 dias terminando hoje."""
    fim = fim or date.today()
    inicio = inicio or fim - timedelta(days=29)
    return (fim, inicio) if inicio > fim else (inicio, fim)


def _variacao(atual: float, anterior: float) -> IndicadorComparado:
    """Sem base de comparação a variação percentual fica nula, não zero."""
    pct = ((atual - anterior) / anterior * 100) if anterior else None
    return IndicadorComparado(atual=atual, anterior=anterior, variacao_pct=pct)


async def _meses_de_recesso(db: AsyncSession) -> set[int]:
    valor = (
        await db.execute(
            text("SELECT valor FROM configuracoes WHERE chave = :chave"),
            {"chave": CHAVE_RECESSO},
        )
    ).scalar_one_or_none()

    meses = set()
    for parte in (valor or "").split(","):
        parte = parte.strip()
        if parte.isdigit() and 1 <= int(parte) <= 12:
            meses.add(int(parte))
    return meses


@router.get("/faturamento", response_model=list[PontoFaturamento])
async def faturamento(
    granularidade: str = Query("semana", pattern="^(semana|mes)$"),
    inicio: date | None = None,
    fim: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Faturamento agrupado por semana ou mês, incluindo períodos sem venda.

    Para o dia a dia use /api/dashboard/vendas-por-dia, que já existe.
    """
    inicio, fim = _periodo_padrao(inicio, fim)
    # Unidade e passo entram no SQL como literais, e nao como parametros: o
    # asyncpg exige timedelta para um parametro do tipo interval, e "1 month"
    # nao existe como timedelta. Os valores vem do dicionario acima, alcancado
    # so pelas duas opcoes que o Query(pattern=...) aceita.
    unidade, passo = GRANULARIDADES[granularidade]

    linhas = (
        await db.execute(
            text(
                f"""
                SELECT p::date                          AS inicio,
                       COALESCE(SUM(v.total), 0)        AS faturamento,
                       COALESCE(SUM(v.custo_total), 0)  AS custo,
                       COALESCE(SUM(v.lucro), 0)        AS lucro,
                       COUNT(v.id)                      AS vendas
                FROM generate_series(
                        DATE_TRUNC('{unidade}', CAST(:inicio AS timestamptz)),
                        DATE_TRUNC('{unidade}', CAST(:fim AS timestamptz)),
                        INTERVAL '{passo}'
                     ) p
                LEFT JOIN vendas v
                       ON v.status = 'concluida'
                      AND DATE_TRUNC('{unidade}', v.data_venda) = p
                      AND v.data_venda::date BETWEEN :inicio AND :fim
                GROUP BY p
                ORDER BY p
                """
            ),
            {"inicio": inicio, "fim": fim},
        )
    ).mappings().all()

    pontos = []
    for linha in linhas:
        faturado, vendas = float(linha["faturamento"]), int(linha["vendas"])
        comeco = linha["inicio"]
        if granularidade == "semana":
            rotulo = f"{comeco.strftime('%d/%m')} a {(comeco + timedelta(days=6)).strftime('%d/%m')}"
        else:
            rotulo = f"{MESES[comeco.month - 1][:3]}/{comeco.year}"

        pontos.append(
            PontoFaturamento(
                periodo=rotulo,
                inicio=comeco,
                faturamento=faturado,
                custo=float(linha["custo"]),
                lucro=float(linha["lucro"]),
                vendas=vendas,
                ticket_medio=round(faturado / vendas, 2) if vendas else 0,
            )
        )
    return pontos


@router.get("/comparativo", response_model=ComparativoPeriodo)
async def comparativo(
    inicio: date | None = None,
    fim: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Compara o período escolhido com o período anterior de mesma duração."""
    inicio, fim = _periodo_padrao(inicio, fim)
    dias = (fim - inicio).days + 1
    fim_anterior = inicio - timedelta(days=1)
    inicio_anterior = fim_anterior - timedelta(days=dias - 1)

    linha = (
        await db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(total) FILTER (WHERE janela = 'atual'), 0)    AS fat_atual,
                    COALESCE(SUM(total) FILTER (WHERE janela = 'anterior'), 0) AS fat_anterior,
                    COALESCE(SUM(lucro) FILTER (WHERE janela = 'atual'), 0)    AS lucro_atual,
                    COALESCE(SUM(lucro) FILTER (WHERE janela = 'anterior'), 0) AS lucro_anterior,
                    COUNT(*) FILTER (WHERE janela = 'atual')                   AS vendas_atual,
                    COUNT(*) FILTER (WHERE janela = 'anterior')                AS vendas_anterior
                FROM (
                    SELECT total, lucro,
                           CASE WHEN data_venda::date BETWEEN :inicio AND :fim
                                THEN 'atual' ELSE 'anterior' END AS janela
                    FROM vendas
                    WHERE status = 'concluida'
                      AND data_venda::date BETWEEN :inicio_anterior AND :fim
                ) v
                """
            ),
            {
                "inicio": inicio,
                "fim": fim,
                "inicio_anterior": inicio_anterior,
            },
        )
    ).mappings().one()

    fat_atual, fat_anterior = float(linha["fat_atual"]), float(linha["fat_anterior"])
    vendas_atual, vendas_anterior = int(linha["vendas_atual"]), int(linha["vendas_anterior"])

    return ComparativoPeriodo(
        inicio=inicio,
        fim=fim,
        inicio_anterior=inicio_anterior,
        fim_anterior=fim_anterior,
        faturamento=_variacao(fat_atual, fat_anterior),
        lucro=_variacao(float(linha["lucro_atual"]), float(linha["lucro_anterior"])),
        vendas=_variacao(vendas_atual, vendas_anterior),
        ticket_medio=_variacao(
            round(fat_atual / vendas_atual, 2) if vendas_atual else 0,
            round(fat_anterior / vendas_anterior, 2) if vendas_anterior else 0,
        ),
    )


@router.get("/produtos", response_model=list[ProdutoRanking])
async def produtos(
    inicio: date | None = None,
    fim: date | None = None,
    limite: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Ranking de produtos dentro do período.

    O /api/dashboard/produtos-mais-vendidos ranqueia desde sempre; aqui o
    recorte acompanha o filtro de data da tela.
    """
    inicio, fim = _periodo_padrao(inicio, fim)

    linhas = (
        await db.execute(
            text(
                """
                SELECT vi.produto_id,
                       COALESCE(p.nome, vi.descricao, 'Sem produto') AS produto,
                       SUM(vi.quantidade)                            AS unidades,
                       SUM(vi.subtotal)                              AS faturamento,
                       SUM(vi.subtotal - vi.quantidade * vi.custo_unitario) AS lucro,
                       SUM(SUM(vi.subtotal)) OVER ()                 AS total_periodo
                FROM venda_itens vi
                JOIN vendas v ON v.id = vi.venda_id AND v.status = 'concluida'
                LEFT JOIN produtos p ON p.id = vi.produto_id
                WHERE v.data_venda::date BETWEEN :inicio AND :fim
                GROUP BY vi.produto_id, COALESCE(p.nome, vi.descricao, 'Sem produto')
                ORDER BY unidades DESC
                LIMIT :limite
                """
            ),
            {"inicio": inicio, "fim": fim, "limite": limite},
        )
    ).mappings().all()

    return [
        ProdutoRanking(
            produto_id=linha["produto_id"],
            produto=linha["produto"],
            unidades=float(linha["unidades"]),
            faturamento=float(linha["faturamento"]),
            lucro=float(linha["lucro"]),
            participacao_pct=round(
                float(linha["faturamento"]) / float(linha["total_periodo"]) * 100, 1
            )
            if float(linha["total_periodo"])
            else 0,
        )
        for linha in linhas
    ]


@router.get("/sazonalidade", response_model=list[MesSazonalidade])
async def sazonalidade(
    anos: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Média de faturamento por mês do ano, para expor quedas sazonais.

    A média divide pelo número de anos que têm venda naquele mês, senão um mês
    presente em dois anos pareceria o dobro de um presente em um só.
    """
    primeiro_ano = date.today().year - anos + 1

    linhas = (
        await db.execute(
            text(
                """
                SELECT EXTRACT(MONTH FROM data_venda)::int          AS mes,
                       SUM(total)                                   AS total,
                       COUNT(*)                                     AS vendas,
                       COUNT(DISTINCT EXTRACT(YEAR FROM data_venda)) AS anos
                FROM vendas
                WHERE status = 'concluida'
                  AND EXTRACT(YEAR FROM data_venda) >= :primeiro_ano
                GROUP BY 1
                """
            ),
            {"primeiro_ano": primeiro_ano},
        )
    ).mappings().all()

    por_mes = {linha["mes"]: linha for linha in linhas}
    recesso = await _meses_de_recesso(db)

    resultado = []
    for mes in range(1, 13):
        linha = por_mes.get(mes)
        total = float(linha["total"]) if linha else 0.0
        anos_com_dados = int(linha["anos"]) if linha else 0
        resultado.append(
            MesSazonalidade(
                mes=mes,
                nome=MESES[mes - 1],
                faturamento_medio=round(total / anos_com_dados, 2) if anos_com_dados else 0,
                faturamento_total=total,
                vendas=int(linha["vendas"]) if linha else 0,
                anos_com_dados=anos_com_dados,
                recesso=mes in recesso,
            )
        )
    return resultado
