-- ============================================================
-- ERP CONFEITARIA - VIEWS DE APOIO (dashboard e relatorios)
-- Rodar depois do schema.sql
-- ============================================================

-- ============================================================
-- FICHA TECNICA: cada linha e um insumo dentro de uma receita,
-- ja com o custo daquela linha na receita.
-- ============================================================
CREATE OR REPLACE VIEW vw_ficha_tecnica AS
SELECT
    r.id                                AS receita_id,
    r.nome                              AS receita,
    r.categoria                         AS receita_categoria,
    r.rendimento,
    r.unidade_rendimento,
    i.id                                AS ingrediente_id,
    i.nome                              AS ingrediente,
    i.categoria                         AS ingrediente_categoria,
    ri.quantidade,
    ri.unidade,
    i.custo_unitario                    AS custo_por_unidade,
    ROUND(converter_unidade(ri.quantidade, ri.unidade, i.unidade_medida)
          * i.custo_unitario, 4)        AS custo_linha,
    ri.observacao
FROM receita_ingredientes ri
JOIN receitas r     ON r.id = ri.receita_id
JOIN ingredientes i ON i.id = ri.ingrediente_id;

-- ============================================================
-- CUSTO CONSOLIDADO POR RECEITA
-- ============================================================
CREATE OR REPLACE VIEW vw_receitas_custo AS
SELECT
    r.id,
    r.nome,
    r.categoria,
    r.rendimento,
    r.unidade_rendimento,
    r.tempo_preparo_min,
    r.custo_total,
    r.custo_unitario,
    r.preco_venda_sugerido,
    COUNT(ri.id)                                    AS qtd_ingredientes,
    CASE WHEN COALESCE(r.preco_venda_sugerido, 0) > 0
         THEN ROUND((r.preco_venda_sugerido - r.custo_unitario)
                    / r.preco_venda_sugerido * 100, 2)
         ELSE NULL
    END                                             AS margem_sugerida_pct,
    r.ativo
FROM receitas r
LEFT JOIN receita_ingredientes ri ON ri.receita_id = r.id
GROUP BY r.id;

-- ============================================================
-- PRODUTOS COM MARGEM
-- ============================================================
CREATE OR REPLACE VIEW vw_produtos_margem AS
SELECT
    p.id,
    p.nome,
    p.categoria,
    p.preco_venda,
    p.custo_unitario,
    p.margem_valor,
    p.margem_lucro,
    r.nome                AS receita,
    r.rendimento,
    p.ativo,
    CASE
        WHEN p.margem_lucro >= 60 THEN 'otima'
        WHEN p.margem_lucro >= 40 THEN 'boa'
        WHEN p.margem_lucro >= 20 THEN 'atencao'
        ELSE 'critica'
    END AS classificacao_margem
FROM produtos p
LEFT JOIN receitas r ON r.id = p.receita_id;

-- ============================================================
-- ESTOQUE: situacao atual de cada insumo
-- ============================================================
CREATE OR REPLACE VIEW vw_estoque AS
SELECT
    i.id,
    i.nome,
    i.categoria,
    i.unidade_medida,
    i.quantidade_atual,
    i.estoque_minimo,
    i.custo_unitario,
    ROUND(i.quantidade_atual * i.custo_unitario, 2) AS valor_em_estoque,
    i.fornecedor,
    i.ativo,
    CASE
        WHEN i.quantidade_atual <= 0                 THEN 'sem_estoque'
        WHEN i.quantidade_atual <= i.estoque_minimo  THEN 'baixo'
        WHEN i.quantidade_atual <= i.estoque_minimo * 1.5 THEN 'atencao'
        ELSE 'ok'
    END AS situacao
FROM ingredientes i;

CREATE OR REPLACE VIEW vw_estoque_baixo AS
SELECT * FROM vw_estoque
WHERE ativo AND situacao IN ('sem_estoque', 'baixo')
ORDER BY quantidade_atual / NULLIF(estoque_minimo, 0) NULLS FIRST, nome;

-- ============================================================
-- VENDAS
-- ============================================================
CREATE OR REPLACE VIEW vw_vendas_detalhe AS
SELECT
    v.id                AS venda_id,
    v.data_venda,
    v.status,
    v.forma_pagamento,
    c.nome              AS cliente,
    vi.id               AS item_id,
    COALESCE(p.nome, vi.descricao) AS produto,
    p.categoria         AS produto_categoria,
    vi.quantidade,
    vi.preco_unitario,
    vi.custo_unitario,
    vi.subtotal,
    ROUND(vi.subtotal - vi.quantidade * vi.custo_unitario, 2) AS lucro_item
FROM venda_itens vi
JOIN vendas v        ON v.id = vi.venda_id
LEFT JOIN produtos p ON p.id = vi.produto_id
LEFT JOIN clientes c ON c.id = v.cliente_id;

CREATE OR REPLACE VIEW vw_vendas_por_dia AS
SELECT
    v.data_venda::date        AS dia,
    COUNT(*)                  AS qtd_vendas,
    SUM(v.total)              AS faturamento,
    SUM(v.custo_total)        AS custo,
    SUM(v.lucro)              AS lucro,
    ROUND(AVG(v.total), 2)    AS ticket_medio
FROM vendas v
WHERE v.status = 'concluida'
GROUP BY 1
ORDER BY 1 DESC;

CREATE OR REPLACE VIEW vw_vendas_por_mes AS
SELECT
    DATE_TRUNC('month', v.data_venda)::date AS mes,
    COUNT(*)                                AS qtd_vendas,
    SUM(v.total)                            AS faturamento,
    SUM(v.custo_total)                      AS custo,
    SUM(v.lucro)                            AS lucro,
    ROUND(AVG(v.total), 2)                  AS ticket_medio
FROM vendas v
WHERE v.status = 'concluida'
GROUP BY 1
ORDER BY 1 DESC;

CREATE OR REPLACE VIEW vw_produtos_mais_vendidos AS
SELECT
    p.id                                 AS produto_id,
    p.nome                               AS produto,
    p.categoria,
    SUM(vi.quantidade)                   AS unidades_vendidas,
    SUM(vi.subtotal)                     AS faturamento,
    SUM(vi.subtotal - vi.quantidade * vi.custo_unitario) AS lucro,
    COUNT(DISTINCT vi.venda_id)          AS aparicoes_em_vendas
FROM venda_itens vi
JOIN vendas v   ON v.id = vi.venda_id AND v.status = 'concluida'
JOIN produtos p ON p.id = vi.produto_id
GROUP BY p.id
ORDER BY unidades_vendidas DESC;

CREATE OR REPLACE VIEW vw_clientes_ranking AS
SELECT
    c.id                     AS cliente_id,
    c.nome                   AS cliente,
    c.telefone,
    COUNT(v.id)              AS qtd_compras,
    COALESCE(SUM(v.total), 0) AS total_gasto,
    ROUND(COALESCE(AVG(v.total), 0), 2) AS ticket_medio,
    MAX(v.data_venda)        AS ultima_compra
FROM clientes c
LEFT JOIN vendas v ON v.cliente_id = c.id AND v.status = 'concluida'
GROUP BY c.id
ORDER BY total_gasto DESC;

-- ============================================================
-- FINANCEIRO
-- ============================================================
CREATE OR REPLACE VIEW vw_fluxo_caixa_mensal AS
SELECT
    DATE_TRUNC('month', t.data_transacao)::date AS mes,
    SUM(t.valor) FILTER (WHERE t.tipo = 'receita') AS receitas,
    SUM(t.valor) FILTER (WHERE t.tipo = 'despesa') AS despesas,
    COALESCE(SUM(t.valor) FILTER (WHERE t.tipo = 'receita'), 0)
      - COALESCE(SUM(t.valor) FILTER (WHERE t.tipo = 'despesa'), 0) AS saldo
FROM transacoes_financeiras t
WHERE t.status = 'pago'
GROUP BY 1
ORDER BY 1 DESC;

CREATE OR REPLACE VIEW vw_despesas_por_categoria AS
SELECT
    t.categoria,
    DATE_TRUNC('month', t.data_transacao)::date AS mes,
    SUM(t.valor) AS total,
    COUNT(*)     AS lancamentos
FROM transacoes_financeiras t
WHERE t.tipo = 'despesa' AND t.status = 'pago'
GROUP BY 1, 2
ORDER BY 2 DESC, 3 DESC;

-- ============================================================
-- KPIs DO DASHBOARD (linha unica)
-- ============================================================
CREATE OR REPLACE VIEW vw_dashboard_kpis AS
SELECT
    (SELECT COALESCE(SUM(total), 0) FROM vendas
      WHERE status = 'concluida' AND data_venda::date = CURRENT_DATE)          AS faturamento_hoje,
    (SELECT COALESCE(SUM(total), 0) FROM vendas
      WHERE status = 'concluida'
        AND data_venda >= DATE_TRUNC('month', CURRENT_DATE))                   AS faturamento_mes,
    (SELECT COALESCE(SUM(lucro), 0) FROM vendas
      WHERE status = 'concluida'
        AND data_venda >= DATE_TRUNC('month', CURRENT_DATE))                   AS lucro_mes,
    (SELECT COUNT(*) FROM vendas
      WHERE status = 'concluida'
        AND data_venda >= DATE_TRUNC('month', CURRENT_DATE))                   AS vendas_mes,
    (SELECT COALESCE(ROUND(AVG(total), 2), 0) FROM vendas
      WHERE status = 'concluida'
        AND data_venda >= DATE_TRUNC('month', CURRENT_DATE))                   AS ticket_medio_mes,
    (SELECT COUNT(*) FROM vw_estoque
      WHERE ativo AND situacao IN ('sem_estoque', 'baixo'))                    AS itens_estoque_baixo,
    (SELECT COALESCE(SUM(quantidade_atual * custo_unitario), 0)
       FROM ingredientes WHERE ativo)                                          AS valor_estoque,
    (SELECT COUNT(*) FROM produtos WHERE ativo)                                AS total_produtos,
    (SELECT COUNT(*) FROM receitas WHERE ativo)                                AS total_receitas,
    (SELECT COUNT(*) FROM clientes WHERE ativo)                                AS total_clientes,
    (SELECT COALESCE(SUM(valor), 0) FROM transacoes_financeiras
      WHERE tipo = 'despesa' AND status = 'pago'
        AND data_transacao >= DATE_TRUNC('month', CURRENT_DATE))               AS despesas_mes;
