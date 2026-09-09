-- ============================================================
-- ERP CONFEITARIA - SEEDS CORRIGIDOS (Cookies + Brownie Recheado)
-- Dados reais de receitas e custos de compra fornecidos pelo usuario
-- ============================================================

-- Configuracoes do sistema (mantidas - nao afetadas por esta correcao)
INSERT INTO configuracoes (chave, valor, tipo, grupo, descricao) VALUES
('empresa_nome', 'Doce Arte Confeitaria', 'string', 'empresa', 'Nome da empresa'),
('empresa_slogan', 'Feito com amor, entregue com sabor', 'string', 'empresa', 'Slogan'),
('moeda', 'BRL', 'string', 'financeiro', 'Moeda padrao'),
('margem_padrao', '60', 'number', 'financeiro', 'Margem de lucro padrao (%)'),
('alerta_estoque_email', 'false', 'boolean', 'alertas', 'Enviar e-mail para estoque baixo'),
('tema_padrao', 'dark', 'string', 'interface', 'Tema padrao da interface'),
('backup_automatico', 'true', 'boolean', 'sistema', 'Backup automatico diario'),
('versao', '1.0.0', 'string', 'sistema', 'Versao do sistema'),
('meses_recesso', '7', 'string', 'analytics', 'Meses de recesso separados por virgula (1-12), destacados no analytics')
ON CONFLICT (chave) DO NOTHING;

-- ============================================================
-- ATENCAO: as linhas abaixo APAGAM todos os dados de
-- categorias, clientes, ingredientes, receitas, produtos
-- e vendas/movimentacoes associadas, para reconstruir tudo
-- com os dados corretos. Rode so este arquivo (nao precisa
-- rodar schema.sql ou views.sql de novo, eles nao mudaram).
-- ============================================================
TRUNCATE TABLE
    movimentacao_estoque,
    venda_itens,
    vendas,
    transacoes_financeiras,
    receita_ingredientes,
    produtos,
    receitas,
    ingredientes,
    clientes,
    categorias
RESTART IDENTITY CASCADE;

-- ============================================================
-- CATEGORIAS
-- ============================================================
INSERT INTO categorias (nome, tipo, cor) VALUES
('Farinha & Amidos', 'ingrediente', '#7C3AED'),
('Acucar & Adocantes', 'ingrediente', '#F59E0B'),
('Gorduras & Oleos', 'ingrediente', '#10B981'),
('Ovos & Laticinios', 'ingrediente', '#EF4444'),
('Cacau & Chocolate', 'ingrediente', '#92400E'),
('Recheios & Cremes', 'ingrediente', '#06B6D4'),
('Fermentos & Aditivos', 'ingrediente', '#6366F1'),
('Brownie', 'produto', '#92400E'),
('Cookie', 'produto', '#F59E0B');

-- ============================================================
-- CLIENTES (exemplo - ajuste com seus clientes reais quando quiser)
-- ============================================================
INSERT INTO clientes (nome, email, telefone, observacoes) VALUES
('Maria Silva', 'maria@email.com', '(54) 99999-1111', 'Cliente frequente'),
('Joao Oliveira', 'joao@email.com', '(54) 99999-2222', 'Compra toda semana'),
('Ana Costa', 'ana@email.com', '(54) 99999-3333', 'Encomenda para eventos'),
('Pedro Santos', NULL, '(54) 99999-4444', 'Aluno da universidade'),
('Carla Mendes', 'carla@email.com', '(54) 99999-5555', 'Pedidos personalizados');

-- ============================================================
-- INGREDIENTES (custo_unitario calculado a partir do preco de compra)
-- ============================================================
INSERT INTO ingredientes (nome, categoria, unidade_medida, quantidade_atual, estoque_minimo, custo_unitario, fornecedor, observacoes) VALUES

-- Massa base dos cookies
('Manteiga Muller', 'Gorduras & Oleos', 'g', 1000, 250, 0.037290, NULL, 'Compra: R$ 37,29/kg'),
('Ovos', 'Ovos & Laticinios', 'unidade', 60, 15, 0.666667, NULL, 'Compra: R$ 20,00 a cartela com 30 ovos'),
('Acucar Refinado', 'Acucar & Adocantes', 'g', 5000, 1000, 0.004000, NULL, 'Compra: R$ 20,00 pacote 5kg - usado em cookies e brownie'),
('Acucar Mascavo', 'Acucar & Adocantes', 'g', 1000, 300, 0.010980, NULL, 'Compra: R$ 10,98/kg'),
('Farinha de Trigo', 'Farinha & Amidos', 'g', 5000, 1000, 0.004000, NULL, 'Compra: R$ 20,00 pacote 5kg - usada em cookies e brownie'),
('Amido de Milho', 'Farinha & Amidos', 'g', 500, 150, 0.009000, NULL, 'Compra: R$ 9,00/kg'),
('Bicarbonato de Sodio', 'Fermentos & Aditivos', 'g', 250, 60, 0.022000, NULL, 'Compra: R$ 5,50 pote 250g'),
('Fermento Quimico', 'Fermentos & Aditivos', 'g', 250, 60, 0.050000, NULL, 'Compra: R$ 12,50 pote 250g'),
('Essencia de Baunilha', 'Fermentos & Aditivos', 'ml', 30, 10, 0.366667, NULL, 'Compra: R$ 11,00 frasco 30ml. 12 gotas =~ 0,6ml (aprox. 20 gotas/ml)'),

-- Chocolates (massa, cobertura e base dos recheios)
('Chocolate Ao Leite Forneavel Harald', 'Cacau & Chocolate', 'g', 1000, 300, 0.039490, NULL, 'Compra: R$ 39,49/kg. Usado como gotas/picado na massa do cookie - ajuste se usar outro chocolate'),
('Chocolate Ao Leite Nobre Sicao', 'Cacau & Chocolate', 'g', 2000, 500, 0.085415, NULL, 'Compra: R$ 170,83 o pacote de 2kg'),
('Chocolate Branco Nobre Sicao', 'Cacau & Chocolate', 'g', 2000, 500, 0.107890, NULL, 'Compra: R$ 215,78 o pacote de 2kg'),
('Chocolate Branco Forneavel Bom Principio', 'Cacau & Chocolate', 'g', 1000, 300, 0.031390, NULL, 'Compra: R$ 31,39/kg'),

-- Recheios prontos / compostos
('Recheio Avela com Chocolate Bom Principio', 'Recheios & Cremes', 'g', 1000, 300, 0.041600, NULL, 'Compra: R$ 41,60/kg - recheio do Cookie Avela'),
('Recheio Chocolate Branco com Cookies Forneavel Doceiro', 'Recheios & Cremes', 'g', 1000, 300, 0.032000, NULL, 'Compra: R$ 32,00/kg - recheio do Cookie Oreo'),
('Recheio Chocolate Branco Red Velvet', 'Recheios & Cremes', 'g', 0, 300, 0.053247, NULL, 'Preparado internamente: mistura de 250g Chocolate Branco Bom Principio + 100g Chocolate Branco Sicao (custo medio ponderado por grama)'),

-- Brownie
('Oleo', 'Gorduras & Oleos', 'ml', 900, 200, 0.010000, NULL, 'Compra: R$ 9,00 garrafa 900ml'),
('Cacau 50% Leke', 'Cacau & Chocolate', 'g', 1000, 250, 0.032640, NULL, 'Compra: R$ 32,64/kg - usado na massa e no recheio do brownie'),
('Cacau 100% Genuine', 'Cacau & Chocolate', 'g', 500, 150, 0.048490, NULL, 'Compra: R$ 48,49/kg - alternativa ao Cacau 50% Leke'),
('Leite Condensado Tirol', 'Ovos & Laticinios', 'g', 5000, 790, 0.010980, NULL, 'Compra: R$ 54,90 o balde de 5kg. 1 caixa =~ 395g'),
('Creme de Leite', 'Ovos & Laticinios', 'g', 5400, 400, 0.011650, NULL, 'Compra: caixa com 27 unidades de 200g por R$ 62,91 (R$ 2,33/unidade)');

-- ============================================================
-- RECEITAS
-- ============================================================
INSERT INTO receitas (nome, categoria, descricao, rendimento, unidade_rendimento, peso_final_g, tempo_preparo_min, preco_venda_sugerido) VALUES
('Cookie Tradicional', 'Cookie', 'Massa base com gotas/pedacos de chocolate, sem recheio', 15, 'unidades', 1500, 40, 5.00),
('Cookie Red Velvet', 'Cookie', 'Massa base recheada com 20g de chocolate branco por cookie', 15, 'unidades', 1800, 50, 7.50),
('Cookie Avela', 'Cookie', 'Massa base recheada com 20g de recheio de avela por cookie', 15, 'unidades', 1800, 50, 7.00),
('Cookie Oreo', 'Cookie', 'Massa base recheada com 20g de recheio chocolate branco com cookies por cookie', 15, 'unidades', 1800, 50, 6.50),
('Brownie Recheado', 'Brownie', 'Brownie de cacau 50% com recheio de leite condensado, creme de leite e cacau', 24, 'quadradinhos', NULL, 75, 9.00);

-- ============================================================
-- INGREDIENTES DE CADA RECEITA
-- ============================================================

-- Cookie Tradicional: massa base completa, incluindo chocolate da massa
INSERT INTO receita_ingredientes (receita_id, ingrediente_id, quantidade, unidade, observacao) VALUES
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Manteiga Muller'), 240, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Ovos'), 2, 'unidade', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Acucar Refinado'), 200, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Acucar Mascavo'), 160, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Farinha de Trigo'), 530, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Amido de Milho'), 60, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Bicarbonato de Sodio'), 6, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Fermento Quimico'), 10, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Essencia de Baunilha'), 0.6, 'ml', 'Equivalente a 12 gotas'),
((SELECT id FROM receitas WHERE nome='Cookie Tradicional'), (SELECT id FROM ingredientes WHERE nome='Chocolate Ao Leite Forneavel Harald'), 300, 'g', 'Gotas/pedacos de chocolate da massa');

-- Cookie Red Velvet: massa base + recheio chocolate branco
INSERT INTO receita_ingredientes (receita_id, ingrediente_id, quantidade, unidade, observacao) VALUES
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Manteiga Muller'), 240, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Ovos'), 2, 'unidade', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Acucar Refinado'), 200, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Acucar Mascavo'), 160, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Farinha de Trigo'), 530, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Amido de Milho'), 60, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Bicarbonato de Sodio'), 6, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Fermento Quimico'), 10, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Essencia de Baunilha'), 0.6, 'ml', 'Equivalente a 12 gotas'),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Chocolate Ao Leite Forneavel Harald'), 300, 'g', 'Gotas/pedacos de chocolate da massa'),
((SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), (SELECT id FROM ingredientes WHERE nome='Recheio Chocolate Branco Red Velvet'), 300, 'g', '20g por cookie x 15 cookies');

-- Cookie Avela: massa base + recheio avela
INSERT INTO receita_ingredientes (receita_id, ingrediente_id, quantidade, unidade, observacao) VALUES
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Manteiga Muller'), 240, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Ovos'), 2, 'unidade', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Acucar Refinado'), 200, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Acucar Mascavo'), 160, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Farinha de Trigo'), 530, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Amido de Milho'), 60, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Bicarbonato de Sodio'), 6, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Fermento Quimico'), 10, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Essencia de Baunilha'), 0.6, 'ml', 'Equivalente a 12 gotas'),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Chocolate Ao Leite Forneavel Harald'), 300, 'g', 'Gotas/pedacos de chocolate da massa'),
((SELECT id FROM receitas WHERE nome='Cookie Avela'), (SELECT id FROM ingredientes WHERE nome='Recheio Avela com Chocolate Bom Principio'), 300, 'g', '20g por cookie x 15 cookies');

-- Cookie Oreo: massa base + recheio chocolate branco com cookies
INSERT INTO receita_ingredientes (receita_id, ingrediente_id, quantidade, unidade, observacao) VALUES
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Manteiga Muller'), 240, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Ovos'), 2, 'unidade', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Acucar Refinado'), 200, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Acucar Mascavo'), 160, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Farinha de Trigo'), 530, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Amido de Milho'), 60, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Bicarbonato de Sodio'), 6, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Fermento Quimico'), 10, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Essencia de Baunilha'), 0.6, 'ml', 'Equivalente a 12 gotas'),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Chocolate Ao Leite Forneavel Harald'), 300, 'g', 'Gotas/pedacos de chocolate da massa'),
((SELECT id FROM receitas WHERE nome='Cookie Oreo'), (SELECT id FROM ingredientes WHERE nome='Recheio Chocolate Branco com Cookies Forneavel Doceiro'), 300, 'g', '20g por cookie x 15 cookies');

-- Brownie Recheado: massa + recheio (rendimento real: 24 quadradinhos)
INSERT INTO receita_ingredientes (receita_id, ingrediente_id, quantidade, unidade, observacao) VALUES
((SELECT id FROM receitas WHERE nome='Brownie Recheado'), (SELECT id FROM ingredientes WHERE nome='Ovos'), 6, 'unidade', NULL),
((SELECT id FROM receitas WHERE nome='Brownie Recheado'), (SELECT id FROM ingredientes WHERE nome='Acucar Refinado'), 500, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Brownie Recheado'), (SELECT id FROM ingredientes WHERE nome='Oleo'), 200, 'ml', NULL),
((SELECT id FROM receitas WHERE nome='Brownie Recheado'), (SELECT id FROM ingredientes WHERE nome='Cacau 50% Leke'), 310, 'g', '250g na massa + 60g no recheio'),
((SELECT id FROM receitas WHERE nome='Brownie Recheado'), (SELECT id FROM ingredientes WHERE nome='Farinha de Trigo'), 230, 'g', NULL),
((SELECT id FROM receitas WHERE nome='Brownie Recheado'), (SELECT id FROM ingredientes WHERE nome='Leite Condensado Tirol'), 790, 'g', '2 caixas (=~395g cada)'),
((SELECT id FROM receitas WHERE nome='Brownie Recheado'), (SELECT id FROM ingredientes WHERE nome='Creme de Leite'), 400, 'g', '2 caixas (=~200g cada)');

-- ============================================================
-- PRODUTOS (itens vendidos ao cliente, vinculados as receitas)
-- ============================================================
INSERT INTO produtos (nome, categoria, descricao, receita_id, preco_venda) VALUES
('Cookie Tradicional', 'Cookie', 'Cookie classico com gotas de chocolate - unidade', (SELECT id FROM receitas WHERE nome='Cookie Tradicional'), 5.00),
('Cookie Red Velvet', 'Cookie', 'Cookie recheado com chocolate branco - unidade', (SELECT id FROM receitas WHERE nome='Cookie Red Velvet'), 7.50),
('Cookie Avela', 'Cookie', 'Cookie recheado com avela e chocolate - unidade', (SELECT id FROM receitas WHERE nome='Cookie Avela'), 7.00),
('Cookie Oreo', 'Cookie', 'Cookie recheado com chocolate branco e cookies - unidade', (SELECT id FROM receitas WHERE nome='Cookie Oreo'), 6.50),
('Brownie Recheado', 'Brownie', 'Brownie de cacau com recheio cremoso - quadradinho', (SELECT id FROM receitas WHERE nome='Brownie Recheado'), 9.00);

-- ============================================================
-- Sincroniza custo_unitario/margem dos produtos com o custo_total
-- ja calculado nas receitas pelos triggers do schema.sql
-- ============================================================
UPDATE receitas SET atualizado_em = atualizado_em;
