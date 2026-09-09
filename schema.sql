-- ============================================================
-- ERP CONFEITARIA - SCHEMA
-- Banco: PostgreSQL 14+
-- Ordem de execucao: schema.sql -> views.sql -> seeds.sql
-- ============================================================

-- ============================================================
-- TIPOS AUXILIARES (via CHECK, para manter simples de migrar)
-- ============================================================

-- ============================================================
-- CONFIGURACOES
-- ============================================================
CREATE TABLE IF NOT EXISTS configuracoes (
    id            SERIAL PRIMARY KEY,
    chave         VARCHAR(100) NOT NULL UNIQUE,
    valor         TEXT,
    tipo          VARCHAR(20)  NOT NULL DEFAULT 'string'
                  CHECK (tipo IN ('string', 'number', 'boolean', 'json')),
    grupo         VARCHAR(50)  NOT NULL DEFAULT 'geral',
    descricao     TEXT,
    atualizado_em TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================================
-- CATEGORIAS (de ingrediente, produto ou financeira)
-- ============================================================
CREATE TABLE IF NOT EXISTS categorias (
    id        SERIAL PRIMARY KEY,
    nome      VARCHAR(100) NOT NULL,
    tipo      VARCHAR(20)  NOT NULL DEFAULT 'ingrediente'
              CHECK (tipo IN ('ingrediente', 'produto', 'financeiro')),
    cor       VARCHAR(9)   NOT NULL DEFAULT '#7C3AED',
    criado_em TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (nome, tipo)
);

-- ============================================================
-- CLIENTES
-- ============================================================
CREATE TABLE IF NOT EXISTS clientes (
    id            SERIAL PRIMARY KEY,
    nome          VARCHAR(150) NOT NULL,
    email         VARCHAR(150),
    telefone      VARCHAR(30),
    observacoes   TEXT,
    ativo         BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clientes_nome ON clientes (LOWER(nome));

-- ============================================================
-- INGREDIENTES (insumos com controle de estoque)
-- ============================================================
CREATE TABLE IF NOT EXISTS ingredientes (
    id               SERIAL PRIMARY KEY,
    nome             VARCHAR(150)   NOT NULL UNIQUE,
    categoria        VARCHAR(100),
    unidade_medida   VARCHAR(20)    NOT NULL DEFAULT 'g'
                     CHECK (unidade_medida IN ('g', 'kg', 'ml', 'l', 'unidade')),
    quantidade_atual NUMERIC(14, 3) NOT NULL DEFAULT 0,
    estoque_minimo   NUMERIC(14, 3) NOT NULL DEFAULT 0,
    -- custo por unidade_medida (ex.: R$ por grama). 6 casas para insumos baratos.
    custo_unitario   NUMERIC(14, 6) NOT NULL DEFAULT 0 CHECK (custo_unitario >= 0),
    fornecedor       VARCHAR(150),
    observacoes      TEXT,
    ativo            BOOLEAN        NOT NULL DEFAULT TRUE,
    criado_em        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    atualizado_em    TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingredientes_categoria ON ingredientes (categoria);

-- ============================================================
-- RECEITAS (fichas tecnicas)
-- ============================================================
CREATE TABLE IF NOT EXISTS receitas (
    id                    SERIAL PRIMARY KEY,
    nome                  VARCHAR(150)   NOT NULL UNIQUE,
    categoria             VARCHAR(100),
    descricao             TEXT,
    rendimento            NUMERIC(12, 3) NOT NULL DEFAULT 1 CHECK (rendimento > 0),
    unidade_rendimento    VARCHAR(30)    NOT NULL DEFAULT 'unidades',
    peso_final_g          NUMERIC(12, 2),
    tempo_preparo_min     INTEGER,
    preco_venda_sugerido  NUMERIC(12, 2),
    -- calculados por trigger a partir de receita_ingredientes
    custo_total           NUMERIC(14, 4) NOT NULL DEFAULT 0,
    custo_unitario        NUMERIC(14, 4) NOT NULL DEFAULT 0,
    ativo                 BOOLEAN        NOT NULL DEFAULT TRUE,
    criado_em             TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    atualizado_em         TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- ============================================================
-- RECEITA x INGREDIENTES
-- ============================================================
CREATE TABLE IF NOT EXISTS receita_ingredientes (
    id             SERIAL PRIMARY KEY,
    receita_id     INTEGER        NOT NULL REFERENCES receitas (id) ON DELETE CASCADE,
    ingrediente_id INTEGER        NOT NULL REFERENCES ingredientes (id) ON DELETE RESTRICT,
    quantidade     NUMERIC(14, 3) NOT NULL CHECK (quantidade > 0),
    unidade        VARCHAR(20)    NOT NULL DEFAULT 'g'
                   CHECK (unidade IN ('g', 'kg', 'ml', 'l', 'unidade')),
    observacao     TEXT,
    UNIQUE (receita_id, ingrediente_id)
);

CREATE INDEX IF NOT EXISTS idx_receita_ing_receita ON receita_ingredientes (receita_id);
CREATE INDEX IF NOT EXISTS idx_receita_ing_ingrediente ON receita_ingredientes (ingrediente_id);

-- ============================================================
-- PRODUTOS (o que e vendido ao cliente)
-- ============================================================
CREATE TABLE IF NOT EXISTS produtos (
    id             SERIAL PRIMARY KEY,
    nome           VARCHAR(150)   NOT NULL UNIQUE,
    categoria      VARCHAR(100),
    descricao      TEXT,
    receita_id     INTEGER        REFERENCES receitas (id) ON DELETE SET NULL,
    preco_venda    NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (preco_venda >= 0),
    -- calculados por trigger a partir da receita vinculada
    custo_unitario NUMERIC(14, 4) NOT NULL DEFAULT 0,
    margem_valor   NUMERIC(14, 4) NOT NULL DEFAULT 0,
    margem_lucro   NUMERIC(8, 2)  NOT NULL DEFAULT 0,
    ativo          BOOLEAN        NOT NULL DEFAULT TRUE,
    criado_em      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    atualizado_em  TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_produtos_receita ON produtos (receita_id);

-- ============================================================
-- VENDAS
-- ============================================================
CREATE TABLE IF NOT EXISTS vendas (
    id              SERIAL PRIMARY KEY,
    cliente_id      INTEGER        REFERENCES clientes (id) ON DELETE SET NULL,
    data_venda      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    subtotal        NUMERIC(14, 2) NOT NULL DEFAULT 0,
    desconto        NUMERIC(14, 2) NOT NULL DEFAULT 0 CHECK (desconto >= 0),
    total           NUMERIC(14, 2) NOT NULL DEFAULT 0,
    custo_total     NUMERIC(14, 4) NOT NULL DEFAULT 0,
    lucro           NUMERIC(14, 4) NOT NULL DEFAULT 0,
    forma_pagamento VARCHAR(30)    NOT NULL DEFAULT 'dinheiro'
                    CHECK (forma_pagamento IN ('dinheiro', 'pix', 'debito', 'credito', 'transferencia', 'fiado')),
    status          VARCHAR(20)    NOT NULL DEFAULT 'concluida'
                    CHECK (status IN ('pendente', 'concluida', 'cancelada')),
    observacoes     TEXT,
    criado_em       TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas (data_venda);
CREATE INDEX IF NOT EXISTS idx_vendas_cliente ON vendas (cliente_id);

CREATE TABLE IF NOT EXISTS venda_itens (
    id             SERIAL PRIMARY KEY,
    venda_id       INTEGER        NOT NULL REFERENCES vendas (id) ON DELETE CASCADE,
    produto_id     INTEGER        REFERENCES produtos (id) ON DELETE SET NULL,
    descricao      VARCHAR(150),
    quantidade     NUMERIC(12, 3) NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(12, 2) NOT NULL CHECK (preco_unitario >= 0),
    custo_unitario NUMERIC(14, 4) NOT NULL DEFAULT 0,
    subtotal       NUMERIC(14, 2) NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_venda_itens_venda ON venda_itens (venda_id);
CREATE INDEX IF NOT EXISTS idx_venda_itens_produto ON venda_itens (produto_id);

-- ============================================================
-- MOVIMENTACAO DE ESTOQUE (kardex dos ingredientes)
-- ============================================================
CREATE TABLE IF NOT EXISTS movimentacao_estoque (
    id                  SERIAL PRIMARY KEY,
    ingrediente_id      INTEGER        NOT NULL REFERENCES ingredientes (id) ON DELETE CASCADE,
    tipo                VARCHAR(20)    NOT NULL
                        CHECK (tipo IN ('entrada', 'saida', 'ajuste', 'perda')),
    quantidade          NUMERIC(14, 3) NOT NULL,
    quantidade_anterior NUMERIC(14, 3) NOT NULL DEFAULT 0,
    quantidade_nova     NUMERIC(14, 3) NOT NULL DEFAULT 0,
    custo_unitario      NUMERIC(14, 6) NOT NULL DEFAULT 0,
    custo_total         NUMERIC(14, 4) NOT NULL DEFAULT 0,
    motivo              TEXT,
    referencia          VARCHAR(100),
    criado_em           TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mov_ingrediente ON movimentacao_estoque (ingrediente_id);
CREATE INDEX IF NOT EXISTS idx_mov_data ON movimentacao_estoque (criado_em);

-- ============================================================
-- TRANSACOES FINANCEIRAS (caixa)
-- ============================================================
CREATE TABLE IF NOT EXISTS transacoes_financeiras (
    id              SERIAL PRIMARY KEY,
    tipo            VARCHAR(20)    NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    categoria       VARCHAR(100)   NOT NULL DEFAULT 'geral',
    descricao       VARCHAR(255)   NOT NULL,
    valor           NUMERIC(14, 2) NOT NULL CHECK (valor >= 0),
    data_transacao  DATE           NOT NULL DEFAULT CURRENT_DATE,
    forma_pagamento VARCHAR(30)    NOT NULL DEFAULT 'dinheiro',
    venda_id        INTEGER        REFERENCES vendas (id) ON DELETE SET NULL,
    status          VARCHAR(20)    NOT NULL DEFAULT 'pago'
                    CHECK (status IN ('pendente', 'pago', 'cancelado')),
    observacoes     TEXT,
    criado_em       TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transacoes_data ON transacoes_financeiras (data_transacao);
CREATE INDEX IF NOT EXISTS idx_transacoes_tipo ON transacoes_financeiras (tipo);
CREATE INDEX IF NOT EXISTS idx_transacoes_venda ON transacoes_financeiras (venda_id);

-- ============================================================
-- FUNCOES AUXILIARES
-- ============================================================

-- Converte uma quantidade para a unidade base do ingrediente.
-- Ex.: 1,5 kg de um ingrediente cadastrado em "g" vira 1500.
CREATE OR REPLACE FUNCTION converter_unidade(
    p_quantidade NUMERIC,
    p_de         VARCHAR,
    p_para       VARCHAR
) RETURNS NUMERIC AS $$
BEGIN
    IF p_de = p_para OR p_de IS NULL OR p_para IS NULL THEN
        RETURN p_quantidade;
    END IF;

    IF p_de = 'kg' AND p_para = 'g'  THEN RETURN p_quantidade * 1000; END IF;
    IF p_de = 'g'  AND p_para = 'kg' THEN RETURN p_quantidade / 1000; END IF;
    IF p_de = 'l'  AND p_para = 'ml' THEN RETURN p_quantidade * 1000; END IF;
    IF p_de = 'ml' AND p_para = 'l'  THEN RETURN p_quantidade / 1000; END IF;

    -- Unidades incompativeis (ex.: g -> unidade): assume 1:1 e nao quebra o calculo.
    RETURN p_quantidade;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Custo total dos insumos de uma receita, ja convertendo unidades.
CREATE OR REPLACE FUNCTION calcular_custo_receita(p_receita_id INTEGER)
RETURNS NUMERIC AS $$
DECLARE
    v_custo NUMERIC(14, 4);
BEGIN
    SELECT COALESCE(SUM(
        converter_unidade(ri.quantidade, ri.unidade, i.unidade_medida) * i.custo_unitario
    ), 0)
    INTO v_custo
    FROM receita_ingredientes ri
    JOIN ingredientes i ON i.id = ri.ingrediente_id
    WHERE ri.receita_id = p_receita_id;

    RETURN v_custo;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- TRIGGERS: CUSTO DAS RECEITAS
-- ============================================================
CREATE OR REPLACE FUNCTION trg_receita_calcular_custo()
RETURNS TRIGGER AS $$
BEGIN
    NEW.custo_total    := calcular_custo_receita(NEW.id);
    NEW.custo_unitario := CASE
        WHEN COALESCE(NEW.rendimento, 0) > 0 THEN NEW.custo_total / NEW.rendimento
        ELSE 0
    END;
    NEW.atualizado_em  := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS receitas_calcular_custo ON receitas;
CREATE TRIGGER receitas_calcular_custo
    BEFORE INSERT OR UPDATE ON receitas
    FOR EACH ROW EXECUTE FUNCTION trg_receita_calcular_custo();

-- Alterou a composicao da receita -> recalcula a receita.
CREATE OR REPLACE FUNCTION trg_receita_ing_sincronizar()
RETURNS TRIGGER AS $$
DECLARE
    v_receita_id INTEGER := COALESCE(NEW.receita_id, OLD.receita_id);
BEGIN
    UPDATE receitas SET atualizado_em = NOW() WHERE id = v_receita_id;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS receita_ingredientes_sincronizar ON receita_ingredientes;
CREATE TRIGGER receita_ingredientes_sincronizar
    AFTER INSERT OR UPDATE OR DELETE ON receita_ingredientes
    FOR EACH ROW EXECUTE FUNCTION trg_receita_ing_sincronizar();

-- Mudou o custo de compra de um insumo -> recalcula toda receita que o usa.
CREATE OR REPLACE FUNCTION trg_ingrediente_propagar_custo()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE receitas r
    SET atualizado_em = NOW()
    WHERE EXISTS (
        SELECT 1 FROM receita_ingredientes ri
        WHERE ri.receita_id = r.id AND ri.ingrediente_id = NEW.id
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ingredientes_propagar_custo ON ingredientes;
CREATE TRIGGER ingredientes_propagar_custo
    AFTER UPDATE OF custo_unitario, unidade_medida ON ingredientes
    FOR EACH ROW
    WHEN (OLD.custo_unitario IS DISTINCT FROM NEW.custo_unitario
       OR OLD.unidade_medida IS DISTINCT FROM NEW.unidade_medida)
    EXECUTE FUNCTION trg_ingrediente_propagar_custo();

-- ============================================================
-- TRIGGERS: CUSTO E MARGEM DOS PRODUTOS
-- ============================================================
CREATE OR REPLACE FUNCTION trg_produto_calcular_margem()
RETURNS TRIGGER AS $$
DECLARE
    v_custo NUMERIC(14, 4) := 0;
BEGIN
    IF NEW.receita_id IS NOT NULL THEN
        SELECT custo_unitario INTO v_custo FROM receitas WHERE id = NEW.receita_id;
    END IF;

    NEW.custo_unitario := COALESCE(v_custo, 0);
    NEW.margem_valor   := NEW.preco_venda - NEW.custo_unitario;
    NEW.margem_lucro   := CASE
        WHEN NEW.preco_venda > 0 THEN ROUND(NEW.margem_valor / NEW.preco_venda * 100, 2)
        ELSE 0
    END;
    NEW.atualizado_em  := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS produtos_calcular_margem ON produtos;
CREATE TRIGGER produtos_calcular_margem
    BEFORE INSERT OR UPDATE ON produtos
    FOR EACH ROW EXECUTE FUNCTION trg_produto_calcular_margem();

-- Receita mudou de custo -> produtos vinculados recalculam a margem.
CREATE OR REPLACE FUNCTION trg_receita_propagar_produtos()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE produtos SET atualizado_em = NOW() WHERE receita_id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS receitas_propagar_produtos ON receitas;
CREATE TRIGGER receitas_propagar_produtos
    AFTER UPDATE ON receitas
    FOR EACH ROW
    WHEN (OLD.custo_unitario IS DISTINCT FROM NEW.custo_unitario)
    EXECUTE FUNCTION trg_receita_propagar_produtos();

-- ============================================================
-- TRIGGERS: TOTAIS DA VENDA
-- ============================================================
CREATE OR REPLACE FUNCTION trg_venda_item_subtotal()
RETURNS TRIGGER AS $$
DECLARE
    v_custo NUMERIC(14, 4);
BEGIN
    IF NEW.custo_unitario = 0 AND NEW.produto_id IS NOT NULL THEN
        SELECT custo_unitario INTO v_custo FROM produtos WHERE id = NEW.produto_id;
        NEW.custo_unitario := COALESCE(v_custo, 0);
    END IF;

    NEW.subtotal := ROUND(NEW.quantidade * NEW.preco_unitario, 2);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS venda_itens_subtotal ON venda_itens;
CREATE TRIGGER venda_itens_subtotal
    BEFORE INSERT OR UPDATE ON venda_itens
    FOR EACH ROW EXECUTE FUNCTION trg_venda_item_subtotal();

CREATE OR REPLACE FUNCTION trg_venda_recalcular_totais()
RETURNS TRIGGER AS $$
DECLARE
    v_venda_id INTEGER := COALESCE(NEW.venda_id, OLD.venda_id);
BEGIN
    UPDATE vendas v
    SET subtotal    = t.subtotal,
        custo_total = t.custo_total,
        total       = GREATEST(t.subtotal - v.desconto, 0),
        lucro       = GREATEST(t.subtotal - v.desconto, 0) - t.custo_total
    FROM (
        SELECT COALESCE(SUM(subtotal), 0)                    AS subtotal,
               COALESCE(SUM(quantidade * custo_unitario), 0) AS custo_total
        FROM venda_itens WHERE venda_id = v_venda_id
    ) t
    WHERE v.id = v_venda_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS venda_itens_recalcular ON venda_itens;
CREATE TRIGGER venda_itens_recalcular
    AFTER INSERT OR UPDATE OR DELETE ON venda_itens
    FOR EACH ROW EXECUTE FUNCTION trg_venda_recalcular_totais();

-- Desconto alterado direto na venda -> recalcula total e lucro.
CREATE OR REPLACE FUNCTION trg_venda_aplicar_desconto()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total := GREATEST(NEW.subtotal - NEW.desconto, 0);
    NEW.lucro := NEW.total - NEW.custo_total;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vendas_aplicar_desconto ON vendas;
CREATE TRIGGER vendas_aplicar_desconto
    BEFORE UPDATE OF desconto ON vendas
    FOR EACH ROW
    WHEN (OLD.desconto IS DISTINCT FROM NEW.desconto)
    EXECUTE FUNCTION trg_venda_aplicar_desconto();

-- ============================================================
-- TRIGGERS: TIMESTAMPS
-- ============================================================
DROP TRIGGER IF EXISTS clientes_timestamp ON clientes;
CREATE TRIGGER clientes_timestamp BEFORE UPDATE ON clientes
    FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();

DROP TRIGGER IF EXISTS ingredientes_timestamp ON ingredientes;
CREATE TRIGGER ingredientes_timestamp BEFORE UPDATE ON ingredientes
    FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();

DROP TRIGGER IF EXISTS configuracoes_timestamp ON configuracoes;
CREATE TRIGGER configuracoes_timestamp BEFORE UPDATE ON configuracoes
    FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();
