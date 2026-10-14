-- ============================================================
-- Correcoes de outubro/2026 para um banco que ja tem dados.
--
-- O schema.sql novo so vale para bancos criados do zero. Este script leva um
-- banco existente (o do Neon, por exemplo) ao mesmo estado, sem apagar nada:
--
--   1. tira 'fiado' das formas de pagamento aceitas
--   2. corrige a data dos lancamentos de venda que caiu no dia seguinte
--      (vendas feitas depois das 21h, gravadas com a data em UTC)
--   3. cria o lancamento que faltou para vendas concluidas de total zero
--      (ex.: venda com desconto igual ao subtotal, que nao entrava no caixa)
--
-- Pode rodar mais de uma vez: cada passo so mexe no que ainda esta errado.
-- Tudo roda numa transacao: se algo falhar, nada e alterado.
--
-- Como rodar: SQL Editor do Neon (cole e execute) ou
--   psql "$DATABASE_URL" -f migracoes/2026-10_correcoes.sql
-- ============================================================

BEGIN;

-- 1. Fiado ----------------------------------------------------
-- Para antes de mexer se ainda houver venda em fiado: a restricao nova as
-- recusaria, e decidir para qual forma elas vao e uma escolha do negocio.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM vendas WHERE forma_pagamento = 'fiado') THEN
        RAISE EXCEPTION 'Ha vendas em fiado. Troque a forma de pagamento delas antes de rodar este script.';
    END IF;
END $$;

ALTER TABLE vendas DROP CONSTRAINT IF EXISTS vendas_forma_pagamento_check;
ALTER TABLE vendas ADD CONSTRAINT vendas_forma_pagamento_check
    CHECK (forma_pagamento IN ('dinheiro', 'pix', 'debito', 'credito', 'transferencia'));

-- 2. Data dos lancamentos de venda ---------------------------
-- O dia certo e o dia da venda no horario de Brasilia.
UPDATE transacoes_financeiras t
SET data_transacao = (v.data_venda AT TIME ZONE 'America/Sao_Paulo')::date
FROM vendas v
WHERE t.venda_id = v.id
  AND t.data_transacao <> (v.data_venda AT TIME ZONE 'America/Sao_Paulo')::date;

-- 3. Lancamento que faltou ------------------------------------
-- Mesmo formato que o sistema grava hoje ao concluir uma venda.
INSERT INTO transacoes_financeiras
    (tipo, categoria, descricao, valor, data_transacao, forma_pagamento, venda_id, status)
SELECT 'receita', 'vendas', 'Venda #' || v.id, v.total,
       (v.data_venda AT TIME ZONE 'America/Sao_Paulo')::date,
       v.forma_pagamento, v.id, 'pago'
FROM vendas v
WHERE v.status = 'concluida'
  AND NOT EXISTS (SELECT 1 FROM transacoes_financeiras t WHERE t.venda_id = v.id);

COMMIT;

-- Conferencia (opcional): toda venda concluida com um lancamento no mesmo dia.
-- SELECT v.id, (v.data_venda AT TIME ZONE 'America/Sao_Paulo')::date AS dia_venda,
--        t.data_transacao, t.valor
-- FROM vendas v LEFT JOIN transacoes_financeiras t ON t.venda_id = v.id
-- WHERE v.status = 'concluida'
-- ORDER BY v.id;
