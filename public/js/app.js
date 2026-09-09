let telaAtual = 'dashboard';
const cache = { produtos: [], receitas: [], ingredientes: [], clientes: [] };

// =====================================================================
// DASHBOARD
// =====================================================================
async function telaDashboard(alvo) {
    const [kpis, porDia, maisVendidos, alertas, margens] = await Promise.all([
        API.get('/dashboard/kpis'),
        API.get('/dashboard/vendas-por-dia?dias=14'),
        API.get('/dashboard/produtos-mais-vendidos?limite=6'),
        API.get('/estoque/alertas'),
        API.get('/dashboard/margem-produtos'),
    ]);

    const kpi = (rotulo, valor, detalhe = '', classe = '', destaque = false) => `
        <div class="card kpi ${destaque ? 'destaque' : ''}">
            <div class="rotulo">${rotulo}</div>
            <div class="valor ${classe}">${valor}</div>
            <div class="detalhe">${detalhe}</div>
        </div>`;

    alvo.innerHTML = `
        <div class="grade grade-kpi">
            ${kpi('Faturamento do mês', moeda(kpis.faturamento_mes), `${kpis.vendas_mes} vendas`, '', true)}
            ${kpi('Lucro do mês', moeda(kpis.lucro_mes), 'receita menos custo dos insumos', 'positivo')}
            ${kpi('Vendido hoje', moeda(kpis.faturamento_hoje))}
            ${kpi('Ticket médio', moeda(kpis.ticket_medio_mes))}
            ${kpi('Saldo do mês', moeda(kpis.saldo_mes), `despesas: ${moeda(kpis.despesas_mes)}`,
                  kpis.saldo_mes >= 0 ? 'positivo' : 'negativo')}
            ${kpi('Valor em estoque', moeda(kpis.valor_estoque),
                  `${kpis.itens_estoque_baixo} item(ns) para repor`,
                  kpis.itens_estoque_baixo ? 'negativo' : '')}
        </div>

        <div class="grade grade-2" style="margin-top:14px">
            <div class="card">
                <h3>Faturamento dos últimos 14 dias</h3>
                ${graficoBarras(porDia)}
            </div>
            <div class="card">
                <h3>Produtos mais vendidos (unidades)</h3>
                ${barrasHorizontais(maisVendidos, (v) => numero(v, 0))}
            </div>
        </div>

        <div class="grade grade-2" style="margin-top:14px">
            <div class="card">
                <h3>Precisa repor</h3>
                ${tabela([
                    { titulo: 'Ingrediente', render: (i) => escapar(i.nome) },
                    { titulo: 'Atual', num: true, render: (i) => `${numero(i.quantidade_atual)} ${i.unidade_medida}` },
                    { titulo: 'Mínimo', num: true, render: (i) => numero(i.estoque_minimo) },
                    { titulo: '', render: (i) => etiqueta(i.situacao, i.situacao.replace('_', ' ')) },
                ], alertas, { vazio: 'Estoque tranquilo, nada abaixo do mínimo.' })}
            </div>
            <div class="card">
                <h3>Margem por produto</h3>
                ${tabela([
                    { titulo: 'Produto', render: (p) => escapar(p.nome) },
                    { titulo: 'Custo', num: true, render: (p) => moeda(p.custo_unitario) },
                    { titulo: 'Venda', num: true, render: (p) => moeda(p.preco_venda) },
                    { titulo: 'Margem', num: true, render: (p) => `${pct(p.margem_lucro)} ${etiqueta(p.classificacao_margem)}` },
                ], margens, { vazio: 'Cadastre produtos para ver as margens.' })}
            </div>
        </div>`;
}

// =====================================================================
// PDV / NOVA VENDA
// =====================================================================
const carrinho = [];

async function telaPdv(alvo) {
    const [produtos, clientes] = await Promise.all([API.get('/produtos'), API.get('/clientes')]);
    cache.produtos = produtos;
    cache.clientes = clientes;

    alvo.innerHTML = `
        <div class="pdv">
            <div class="card">
                <h3>Escolha os produtos</h3>
                <div class="catalogo">
                    ${produtos.map((p) => `
                        <button class="produto-btn" onclick="adicionarAoCarrinho(${p.id})">
                            <strong>${escapar(p.nome)}</strong>
                            <small>${escapar(p.categoria || '')} · custo ${moeda(p.custo_unitario)}</small>
                            <span class="preco">${moeda(p.preco_venda)}</span>
                        </button>`).join('') || '<div class="vazio">Cadastre produtos primeiro.</div>'}
                </div>
            </div>

            <div class="card">
                <h3>Carrinho</h3>
                <div id="carrinho"></div>
                <div class="linha-form" style="margin-top:14px">
                    ${selecao('Cliente', 'cliente_id', [['', 'Consumidor final'], ...clientes.map((c) => [c.id, c.nome])])}
                    ${selecao('Pagamento', 'forma_pagamento', [
                        ['dinheiro', 'Dinheiro'], ['pix', 'Pix'], ['debito', 'Débito'],
                        ['credito', 'Crédito'], ['transferencia', 'Transferência'], ['fiado', 'Fiado'],
                    ])}
                    ${campo('Desconto (R$)', 'desconto', '0', 'number', 'min="0" step="0.01" oninput="desenharCarrinho()"')}
                </div>
                <div style="margin-top:12px">
                    <label style="display:flex;gap:8px;align-items:center">
                        <input type="checkbox" id="f-baixar" checked style="width:auto">
                        Dar baixa nos ingredientes do estoque
                    </label>
                </div>
                <button class="primario" style="width:100%;justify-content:center;margin-top:14px"
                        onclick="finalizarVenda()">Finalizar venda</button>
            </div>
        </div>`;

    desenharCarrinho();
}

function adicionarAoCarrinho(produtoId) {
    const produto = cache.produtos.find((p) => p.id === produtoId);
    const existente = carrinho.find((i) => i.produto_id === produtoId);
    if (existente) existente.quantidade += 1;
    else carrinho.push({ produto_id: produtoId, nome: produto.nome, quantidade: 1, preco: produto.preco_venda, custo: produto.custo_unitario });
    desenharCarrinho();
}

function alterarItem(indice, campo, valor) {
    const numeroValor = Number(valor);
    if (campo === 'quantidade' && numeroValor <= 0) return removerDoCarrinho(indice);
    carrinho[indice][campo] = numeroValor;
    desenharCarrinho();
}

function removerDoCarrinho(indice) {
    carrinho.splice(indice, 1);
    desenharCarrinho();
}

function desenharCarrinho() {
    const area = document.getElementById('carrinho');
    if (!area) return;

    if (!carrinho.length) {
        area.innerHTML = '<div class="vazio">Clique nos produtos para montar a venda.</div>';
        return;
    }

    const subtotal = carrinho.reduce((s, i) => s + i.quantidade * i.preco, 0);
    const custo = carrinho.reduce((s, i) => s + i.quantidade * i.custo, 0);
    const desconto = Number(document.getElementById('f-desconto')?.value || 0);
    const total = Math.max(subtotal - desconto, 0);

    area.innerHTML = carrinho.map((item, i) => `
        <div class="carrinho-linha">
            <span class="nome">${escapar(item.nome)}</span>
            <input type="number" min="0" step="1" value="${item.quantidade}"
                   onchange="alterarItem(${i}, 'quantidade', this.value)" title="Quantidade">
            <input type="number" min="0" step="0.01" value="${item.preco}"
                   onchange="alterarItem(${i}, 'preco', this.value)" title="Preço unitário">
            <span class="num" style="width:70px">${moeda(item.quantidade * item.preco)}</span>
            <button class="pequeno perigo" onclick="removerDoCarrinho(${i})">×</button>
        </div>`).join('')
        + `<div style="margin-top:12px">
            <div class="total-linha"><span>Subtotal</span><span>${moeda(subtotal)}</span></div>
            <div class="total-linha"><span>Desconto</span><span>- ${moeda(desconto)}</span></div>
            <div class="total-linha"><span>Custo dos insumos</span><span>${moeda(custo)}</span></div>
            <div class="total-linha"><span>Lucro estimado</span><span class="valor positivo">${moeda(total - custo)}</span></div>
            <div class="total-linha grande"><span>Total</span><span>${moeda(total)}</span></div>
        </div>`;
}

async function finalizarVenda() {
    if (!carrinho.length) return avisar('Adicione ao menos um produto.', 'erro');

    const corpo = {
        cliente_id: document.getElementById('f-cliente_id').value || null,
        forma_pagamento: document.getElementById('f-forma_pagamento').value,
        desconto: Number(document.getElementById('f-desconto').value || 0),
        baixar_estoque: document.getElementById('f-baixar').checked,
        itens: carrinho.map((i) => ({
            produto_id: i.produto_id,
            quantidade: i.quantidade,
            preco_unitario: i.preco,
        })),
    };
    if (corpo.cliente_id) corpo.cliente_id = Number(corpo.cliente_id);

    const venda = await comErro(() => API.post('/vendas', corpo));
    avisar(`Venda #${venda.id} registrada: ${moeda(venda.total)}`);
    carrinho.length = 0;
    irPara('vendas');
}

// =====================================================================
// VENDAS
// =====================================================================
async function telaVendas(alvo) {
    const inicio = document.getElementById('filtro-inicio')?.value || '';
    const fim = document.getElementById('filtro-fim')?.value || '';
    const vendas = await API.get(`/vendas${params({ inicio, fim, limite: 200 })}`);

    const faturado = vendas.filter((v) => v.status === 'concluida').reduce((s, v) => s + v.total, 0);
    const lucro = vendas.filter((v) => v.status === 'concluida').reduce((s, v) => s + v.lucro, 0);

    alvo.innerHTML = `
        <div class="filtros">
            <div><label>De</label><input type="date" id="filtro-inicio" value="${inicio}"></div>
            <div><label>Até</label><input type="date" id="filtro-fim" value="${fim}"></div>
            <button onclick="recarregar()">Filtrar</button>
            <button onclick="document.getElementById('filtro-inicio').value='';document.getElementById('filtro-fim').value='';recarregar()">Limpar</button>
            <a class="botao" href="/api/relatorios/vendas.xlsx${params({ inicio, fim })}">⬇ Excel</a>
        </div>

        <div class="grade grade-kpi" style="margin-bottom:14px">
            <div class="card kpi"><div class="rotulo">Vendas listadas</div><div class="valor">${vendas.length}</div></div>
            <div class="card kpi"><div class="rotulo">Faturamento</div><div class="valor">${moeda(faturado)}</div></div>
            <div class="card kpi"><div class="rotulo">Lucro</div><div class="valor positivo">${moeda(lucro)}</div></div>
        </div>

        <div class="card">
            ${tabela([
                { titulo: '#', render: (v) => v.id },
                { titulo: 'Data', render: (v) => dataHora(v.data_venda) },
                { titulo: 'Cliente', render: (v) => escapar(v.cliente_nome || 'Consumidor final') },
                { titulo: 'Itens', render: (v) => v.itens.map((i) => `${numero(i.quantidade, 0)}x ${escapar(i.descricao || '')}`).join('<br>') },
                { titulo: 'Pagamento', render: (v) => escapar(v.forma_pagamento) },
                { titulo: 'Total', num: true, render: (v) => moeda(v.total) },
                { titulo: 'Lucro', num: true, render: (v) => moeda(v.lucro) },
                { titulo: 'Status', render: (v) => etiqueta(v.status) },
                {
                    titulo: '', render: (v) => v.status === 'cancelada' ? '' :
                        `<div class="acoes-linha"><button class="pequeno perigo" onclick="cancelarVenda(${v.id})">Cancelar</button></div>`,
                },
            ], vendas, { vazio: 'Nenhuma venda no período.' })}
        </div>`;
}

async function cancelarVenda(id) {
    if (!confirm(`Cancelar a venda #${id}? Os ingredientes voltam para o estoque.`)) return;
    await comErro(() => API.post(`/vendas/${id}/cancelar`), 'Venda cancelada e estoque estornado.');
    recarregar();
}

// =====================================================================
// PRODUTOS
// =====================================================================
async function telaProdutos(alvo) {
    const [produtos, receitas] = await Promise.all([
        API.get('/produtos?apenas_ativos=false'),
        API.get('/receitas'),
    ]);
    cache.receitas = receitas;

    alvo.innerHTML = `<div class="card">${tabela([
        { titulo: 'Produto', render: (p) => `<strong>${escapar(p.nome)}</strong><br><small style="color:var(--texto-fraco)">${escapar(p.categoria || '')}</small>` },
        { titulo: 'Receita', render: (p) => escapar(p.receita_nome || '—') },
        { titulo: 'Custo', num: true, render: (p) => moeda(p.custo_unitario) },
        { titulo: 'Preço', num: true, render: (p) => moeda(p.preco_venda) },
        { titulo: 'Lucro/un.', num: true, render: (p) => moeda(p.margem_valor) },
        { titulo: 'Margem', num: true, render: (p) => pct(p.margem_lucro) },
        { titulo: 'Status', render: (p) => p.ativo ? etiqueta('ok', 'ativo') : etiqueta('neutra', 'inativo') },
        {
            titulo: '', render: (p) => `<div class="acoes-linha">
                <button class="pequeno" onclick="sugerirPreco(${p.id})">Preço ideal</button>
                <button class="pequeno" onclick="formProduto(${p.id})">Editar</button>
                <button class="pequeno perigo" onclick="excluir('produtos', ${p.id})">Excluir</button>
            </div>`,
        },
    ], produtos, { vazio: 'Nenhum produto cadastrado.' })}</div>`;
}

async function formProduto(id) {
    const produto = id ? await API.get(`/produtos/${id}`) : {};
    if (!cache.receitas.length) cache.receitas = await API.get('/receitas');

    abrirModal(id ? 'Editar produto' : 'Novo produto', `
        <form class="formulario" onsubmit="salvarProduto(event, ${id || 'null'})">
            <div class="linha-form">
                ${campo('Nome', 'nome', produto.nome || '', 'text', 'required')}
                ${campo('Categoria', 'categoria', produto.categoria || '')}
            </div>
            <div class="linha-form">
                ${selecao('Receita (define o custo)', 'receita_id',
                    [['', 'Sem receita vinculada'], ...cache.receitas.map((r) => [r.id, `${r.nome} — ${moeda(r.custo_unitario)}/un.`])],
                    produto.receita_id || '')}
                ${campo('Preço de venda', 'preco_venda', produto.preco_venda ?? '', 'number', 'step="0.01" min="0" required')}
            </div>
            ${areaTexto('Descrição', 'descricao', produto.descricao || '')}
            <div class="rodape-modal">
                <button type="button" onclick="fecharModal()">Cancelar</button>
                <button type="submit" class="primario">Salvar</button>
            </div>
        </form>`);
}

async function salvarProduto(evento, id) {
    evento.preventDefault();
    const dados = dadosFormulario(evento.target);
    dados.receita_id = dados.receita_id ? Number(dados.receita_id) : null;
    await comErro(() => (id ? API.put(`/produtos/${id}`, dados) : API.post('/produtos', dados)), 'Produto salvo.');
    fecharModal();
    recarregar();
}

async function sugerirPreco(id) {
    const margem = prompt('Qual margem de lucro você quer (%)?', '60');
    if (margem === null) return;
    const r = await comErro(() => API.get(`/produtos/${id}/preco-sugerido?margem=${Number(margem)}`));
    abrirModal('Preço sugerido', `
        <p style="margin-bottom:14px">Para <strong>${escapar(r.produto)}</strong> ter margem de ${pct(r.margem_desejada)}:</p>
        <div class="grade grade-kpi">
            <div class="card kpi"><div class="rotulo">Custo</div><div class="valor">${moeda(r.custo_unitario)}</div></div>
            <div class="card kpi"><div class="rotulo">Preço atual</div><div class="valor">${moeda(r.preco_atual)}</div></div>
            <div class="card kpi destaque"><div class="rotulo">Preço sugerido</div><div class="valor">${moeda(r.preco_sugerido)}</div></div>
        </div>
        <div class="rodape-modal">
            <button onclick="fecharModal()">Fechar</button>
            <button class="primario" onclick="aplicarPreco(${id}, ${r.preco_sugerido})">Usar esse preço</button>
        </div>`);
}

async function aplicarPreco(id, preco) {
    await comErro(() => API.put(`/produtos/${id}`, { preco_venda: preco }), 'Preço atualizado.');
    fecharModal();
    recarregar();
}

// =====================================================================
// RECEITAS
// =====================================================================
async function telaReceitas(alvo) {
    const receitas = await API.get('/receitas?apenas_ativas=false');

    alvo.innerHTML = `<div class="card">${tabela([
        { titulo: 'Receita', render: (r) => `<strong>${escapar(r.nome)}</strong><br><small style="color:var(--texto-fraco)">${escapar(r.categoria || '')}</small>` },
        { titulo: 'Rendimento', num: true, render: (r) => `${numero(r.rendimento, 0)} ${escapar(r.unidade_rendimento)}` },
        { titulo: 'Custo total', num: true, render: (r) => moeda(r.custo_total) },
        { titulo: 'Custo/un.', num: true, render: (r) => moeda(r.custo_unitario) },
        { titulo: 'Preço sugerido', num: true, render: (r) => r.preco_venda_sugerido ? moeda(r.preco_venda_sugerido) : '—' },
        {
            titulo: '', render: (r) => `<div class="acoes-linha">
                <button class="pequeno" onclick="verFicha(${r.id})">Ficha</button>
                <button class="pequeno sucesso" onclick="produzir(${r.id})">Produzir</button>
                <button class="pequeno" onclick="formReceita(${r.id})">Editar</button>
            </div>`,
        },
    ], receitas, { vazio: 'Nenhuma receita cadastrada.' })}</div>`;
}

async function verFicha(id) {
    const r = await API.get(`/receitas/${id}`);
    abrirModal(`Ficha técnica — ${r.nome}`, `
        <div class="grade grade-kpi" style="margin-bottom:16px">
            <div class="card kpi"><div class="rotulo">Custo total</div><div class="valor">${moeda(r.custo_total)}</div></div>
            <div class="card kpi"><div class="rotulo">Custo por unidade</div><div class="valor">${moeda(r.custo_unitario)}</div></div>
            <div class="card kpi"><div class="rotulo">Rendimento</div><div class="valor">${numero(r.rendimento, 0)}</div><div class="detalhe">${escapar(r.unidade_rendimento)}</div></div>
        </div>
        ${tabela([
            { titulo: 'Ingrediente', render: (i) => escapar(i.ingrediente_nome) },
            { titulo: 'Quantidade', num: true, render: (i) => `${numero(i.quantidade, 3)} ${i.unidade}` },
            { titulo: 'Custo', num: true, render: (i) => moeda(i.custo_linha) },
            { titulo: '% do custo', num: true, render: (i) => pct(r.custo_total ? (i.custo_linha / r.custo_total) * 100 : 0) },
        ], [...r.ingredientes].sort((a, b) => b.custo_linha - a.custo_linha))}
        <div class="rodape-modal">
            <a class="botao" href="/api/relatorios/ficha-tecnica/${id}.pdf" target="_blank">⬇ PDF</a>
            <button class="primario" onclick="fecharModal()">Fechar</button>
        </div>`);
}

async function produzir(id) {
    const lotes = prompt('Quantas receitas completas você vai produzir?', '1');
    if (lotes === null) return;
    const r = await comErro(() => API.post(`/receitas/${id}/produzir`, { lotes: Number(lotes) }));
    avisar(`Produzidas ${numero(r.unidades_produzidas, 0)} unidades — custo ${moeda(r.custo_total)}`);
    recarregar();
}

async function formReceita(id) {
    const [receita, ingredientes] = await Promise.all([
        id ? API.get(`/receitas/${id}`) : Promise.resolve({ ingredientes: [] }),
        API.get('/ingredientes'),
    ]);
    cache.ingredientes = ingredientes;

    abrirModal(id ? 'Editar receita' : 'Nova receita', `
        <form class="formulario" onsubmit="salvarReceita(event, ${id || 'null'})">
            <div class="linha-form">
                ${campo('Nome', 'nome', receita.nome || '', 'text', 'required')}
                ${campo('Categoria', 'categoria', receita.categoria || '')}
            </div>
            <div class="linha-form">
                ${campo('Rendimento', 'rendimento', receita.rendimento ?? 1, 'number', 'step="0.001" min="0.001" required')}
                ${campo('Unidade do rendimento', 'unidade_rendimento', receita.unidade_rendimento || 'unidades')}
                ${campo('Tempo de preparo (min)', 'tempo_preparo_min', receita.tempo_preparo_min ?? '', 'number', 'min="0"')}
                ${campo('Preço sugerido', 'preco_venda_sugerido', receita.preco_venda_sugerido ?? '', 'number', 'step="0.01" min="0"')}
            </div>
            ${areaTexto('Descrição / modo de preparo', 'descricao', receita.descricao || '')}

            <div>
                <label>Ingredientes</label>
                <div id="linhas-ingredientes"></div>
                <button type="button" class="pequeno" onclick="adicionarLinhaIngrediente()">+ ingrediente</button>
            </div>

            <div class="rodape-modal">
                <button type="button" onclick="fecharModal()">Cancelar</button>
                <button type="submit" class="primario">Salvar</button>
            </div>
        </form>`);

    (receita.ingredientes || []).forEach((i) => adicionarLinhaIngrediente(i));
    if (!receita.ingredientes?.length) adicionarLinhaIngrediente();
}

function adicionarLinhaIngrediente(item = {}) {
    const area = document.getElementById('linhas-ingredientes');
    const div = document.createElement('div');
    div.className = 'carrinho-linha linha-ingrediente';
    div.innerHTML = `
        <select class="ing-id" style="flex:1">
            ${cache.ingredientes.map((i) =>
                `<option value="${i.id}" data-unidade="${i.unidade_medida}" ${i.id === item.ingrediente_id ? 'selected' : ''}>
                    ${escapar(i.nome)} (${i.unidade_medida})
                </option>`).join('')}
        </select>
        <input class="ing-qtd" type="number" step="0.001" min="0.001" style="width:90px"
               value="${item.quantidade ?? ''}" placeholder="qtd" required>
        <select class="ing-un" style="width:90px">
            ${['g', 'kg', 'ml', 'l', 'unidade'].map((u) =>
                `<option ${u === (item.unidade || 'g') ? 'selected' : ''}>${u}</option>`).join('')}
        </select>
        <button type="button" class="pequeno perigo" onclick="this.parentElement.remove()">×</button>`;
    area.appendChild(div);
}

async function salvarReceita(evento, id) {
    evento.preventDefault();
    const dados = dadosFormulario(evento.target);

    dados.ingredientes = [...document.querySelectorAll('.linha-ingrediente')].map((linha) => ({
        ingrediente_id: Number(linha.querySelector('.ing-id').value),
        quantidade: Number(linha.querySelector('.ing-qtd').value),
        unidade: linha.querySelector('.ing-un').value,
    })).filter((i) => i.quantidade > 0);

    await comErro(() => (id ? API.put(`/receitas/${id}`, dados) : API.post('/receitas', dados)), 'Receita salva.');
    fecharModal();
    recarregar();
}

// =====================================================================
// INGREDIENTES
// =====================================================================
async function telaIngredientes(alvo) {
    const ingredientes = await API.get('/ingredientes?apenas_ativos=false');

    alvo.innerHTML = `<div class="card">${tabela([
        { titulo: 'Ingrediente', render: (i) => `<strong>${escapar(i.nome)}</strong><br><small style="color:var(--texto-fraco)">${escapar(i.categoria || '')}</small>` },
        { titulo: 'Estoque', num: true, render: (i) => `${numero(i.quantidade_atual, 3)} ${i.unidade_medida}` },
        { titulo: 'Mínimo', num: true, render: (i) => numero(i.estoque_minimo, 3) },
        { titulo: 'Custo unit.', num: true, render: (i) => `R$ ${numero(i.custo_unitario, 6)}` },
        { titulo: 'Em estoque', num: true, render: (i) => moeda(i.quantidade_atual * i.custo_unitario) },
        {
            titulo: '', render: (i) => `<div class="acoes-linha">
                <button class="pequeno" onclick="formPrecoCompra(${i.id})">Compra</button>
                <button class="pequeno" onclick="formIngrediente(${i.id})">Editar</button>
                <button class="pequeno perigo" onclick="excluir('ingredientes', ${i.id})">Excluir</button>
            </div>`,
        },
    ], ingredientes, { vazio: 'Nenhum ingrediente cadastrado.' })}</div>`;
}

async function formIngrediente(id) {
    const ing = id ? await API.get(`/ingredientes/${id}`) : {};
    const unidades = [['g', 'gramas'], ['kg', 'quilos'], ['ml', 'mililitros'], ['l', 'litros'], ['unidade', 'unidade']];

    abrirModal(id ? 'Editar ingrediente' : 'Novo ingrediente', `
        <form class="formulario" onsubmit="salvarIngrediente(event, ${id || 'null'})">
            <div class="linha-form">
                ${campo('Nome', 'nome', ing.nome || '', 'text', 'required')}
                ${campo('Categoria', 'categoria', ing.categoria || '')}
                ${selecao('Unidade de medida', 'unidade_medida', unidades, ing.unidade_medida || 'g')}
            </div>
            <div class="linha-form">
                ${campo('Quantidade em estoque', 'quantidade_atual', ing.quantidade_atual ?? 0, 'number', 'step="0.001"')}
                ${campo('Estoque mínimo', 'estoque_minimo', ing.estoque_minimo ?? 0, 'number', 'step="0.001"')}
                ${campo('Custo por unidade (R$)', 'custo_unitario', ing.custo_unitario ?? 0, 'number', 'step="0.000001" min="0"')}
                ${campo('Fornecedor', 'fornecedor', ing.fornecedor || '')}
            </div>
            ${areaTexto('Observações', 'observacoes', ing.observacoes || '')}
            <div class="rodape-modal">
                <button type="button" onclick="fecharModal()">Cancelar</button>
                <button type="submit" class="primario">Salvar</button>
            </div>
        </form>`);
}

async function salvarIngrediente(evento, id) {
    evento.preventDefault();
    const dados = dadosFormulario(evento.target);
    await comErro(() => (id ? API.put(`/ingredientes/${id}`, dados) : API.post('/ingredientes', dados)), 'Ingrediente salvo.');
    fecharModal();
    recarregar();
}

async function formPrecoCompra(id) {
    const ing = await API.get(`/ingredientes/${id}`);
    abrirModal(`Compra — ${ing.nome}`, `
        <p style="color:var(--texto-fraco);margin-bottom:14px">
            Informe quanto pagou e o tamanho da embalagem. O custo por ${ing.unidade_medida}
            é recalculado e as receitas que usam esse insumo se atualizam sozinhas.
        </p>
        <form class="formulario" onsubmit="salvarPrecoCompra(event, ${id})">
            <div class="linha-form">
                ${campo('Quanto pagou (R$)', 'preco_pago', '', 'number', 'step="0.01" min="0.01" required')}
                ${campo('Quantidade da embalagem', 'quantidade_embalagem', '', 'number', 'step="0.001" min="0.001" required')}
                ${selecao('Unidade da embalagem', 'unidade_embalagem',
                    [['g', 'g'], ['kg', 'kg'], ['ml', 'ml'], ['l', 'l'], ['unidade', 'unidade']], ing.unidade_medida)}
            </div>
            <label style="display:flex;gap:8px;align-items:center">
                <input type="checkbox" name="lancar_entrada" checked style="width:auto"> Somar essa quantidade ao estoque
            </label>
            <div class="rodape-modal">
                <button type="button" onclick="fecharModal()">Cancelar</button>
                <button type="submit" class="primario">Registrar compra</button>
            </div>
        </form>`);
}

async function salvarPrecoCompra(evento, id) {
    evento.preventDefault();
    const dados = dadosFormulario(evento.target);
    const ing = await comErro(() => API.post(`/ingredientes/${id}/preco-compra`, dados));
    avisar(`Custo atualizado: R$ ${numero(ing.custo_unitario, 6)} por ${ing.unidade_medida}`);
    fecharModal();
    recarregar();
}

// =====================================================================
// ESTOQUE
// =====================================================================
async function telaEstoque(alvo) {
    const [estoque, movimentos, compras] = await Promise.all([
        API.get('/estoque'),
        API.get('/estoque/movimentacoes?limite=40'),
        API.get('/relatorios/lista-compras'),
    ]);

    alvo.innerHTML = `
        <div class="grade grade-kpi" style="margin-bottom:14px">
            <div class="card kpi"><div class="rotulo">Valor total em estoque</div>
                <div class="valor">${moeda(estoque.reduce((s, i) => s + i.valor_em_estoque, 0))}</div></div>
            <div class="card kpi"><div class="rotulo">Itens para repor</div>
                <div class="valor ${compras.itens.length ? 'negativo' : ''}">${compras.itens.length}</div></div>
            <div class="card kpi"><div class="rotulo">Custo estimado da reposição</div>
                <div class="valor">${moeda(compras.custo_total_estimado)}</div></div>
        </div>

        <div class="card" style="margin-bottom:14px">
            <h3>Situação do estoque</h3>
            ${tabela([
                { titulo: 'Ingrediente', render: (i) => escapar(i.nome) },
                { titulo: 'Categoria', render: (i) => escapar(i.categoria || '—') },
                { titulo: 'Atual', num: true, render: (i) => `${numero(i.quantidade_atual, 3)} ${i.unidade_medida}` },
                { titulo: 'Mínimo', num: true, render: (i) => numero(i.estoque_minimo, 3) },
                { titulo: 'Valor', num: true, render: (i) => moeda(i.valor_em_estoque) },
                { titulo: 'Situação', render: (i) => etiqueta(i.situacao, i.situacao.replace('_', ' ')) },
                {
                    titulo: '', render: (i) => `<div class="acoes-linha">
                        <button class="pequeno" onclick="formMovimentacao(${i.id})">Movimentar</button>
                    </div>`,
                },
            ], estoque)}
        </div>

        <div class="grade grade-2">
            <div class="card">
                <h3>Lista de compras</h3>
                ${tabela([
                    { titulo: 'Ingrediente', render: (i) => escapar(i.ingrediente) },
                    { titulo: 'Comprar', num: true, render: (i) => `${numero(i.comprar, 3)} ${i.unidade}` },
                    { titulo: 'Custo est.', num: true, render: (i) => moeda(i.custo_estimado) },
                ], compras.itens, { vazio: 'Nada para comprar agora.' })}
            </div>
            <div class="card">
                <h3>Últimas movimentações</h3>
                ${tabela([
                    { titulo: 'Quando', render: (m) => dataHora(m.criado_em) },
                    { titulo: 'Ingrediente', render: (m) => escapar(m.ingrediente_nome) },
                    { titulo: 'Tipo', render: (m) => etiqueta(m.tipo === 'entrada' ? 'ok' : 'baixo', m.tipo) },
                    { titulo: 'Qtd', num: true, render: (m) => numero(m.quantidade, 3) },
                    { titulo: 'Saldo', num: true, render: (m) => numero(m.quantidade_nova, 3) },
                ], movimentos, { vazio: 'Sem movimentações ainda.' })}
            </div>
        </div>`;
}

async function formMovimentacao(ingredienteId) {
    const ing = await API.get(`/ingredientes/${ingredienteId}`);
    abrirModal(`Movimentar — ${ing.nome}`, `
        <p style="color:var(--texto-fraco);margin-bottom:14px">
            Estoque atual: <strong>${numero(ing.quantidade_atual, 3)} ${ing.unidade_medida}</strong>.
            Em "ajuste", informe a contagem final que você fez.
        </p>
        <form class="formulario" onsubmit="salvarMovimentacao(event, ${ingredienteId})">
            <div class="linha-form">
                ${selecao('Tipo', 'tipo', [
                    ['entrada', 'Entrada (compra)'], ['saida', 'Saída (uso)'],
                    ['perda', 'Perda / desperdício'], ['ajuste', 'Ajuste de inventário'],
                ])}
                ${campo(`Quantidade (${ing.unidade_medida})`, 'quantidade', '', 'number', 'step="0.001" min="0.001" required')}
            </div>
            ${campo('Motivo', 'motivo', '')}
            <div class="rodape-modal">
                <button type="button" onclick="fecharModal()">Cancelar</button>
                <button type="submit" class="primario">Registrar</button>
            </div>
        </form>`);
}

async function salvarMovimentacao(evento, ingredienteId) {
    evento.preventDefault();
    const dados = { ...dadosFormulario(evento.target), ingrediente_id: ingredienteId };
    await comErro(() => API.post('/estoque/movimentacoes', dados), 'Movimentação registrada.');
    fecharModal();
    recarregar();
}

// =====================================================================
// CLIENTES
// =====================================================================
async function telaClientes(alvo) {
    const clientes = await API.get('/clientes?apenas_ativos=false');

    alvo.innerHTML = `<div class="card">${tabela([
        { titulo: 'Nome', render: (c) => `<strong>${escapar(c.nome)}</strong>` },
        { titulo: 'Telefone', render: (c) => escapar(c.telefone || '—') },
        { titulo: 'E-mail', render: (c) => escapar(c.email || '—') },
        { titulo: 'Observações', render: (c) => escapar(c.observacoes || '') },
        { titulo: 'Status', render: (c) => c.ativo ? etiqueta('ok', 'ativo') : etiqueta('neutra', 'inativo') },
        {
            titulo: '', render: (c) => `<div class="acoes-linha">
                <button class="pequeno" onclick="formCliente(${c.id})">Editar</button>
                <button class="pequeno perigo" onclick="excluir('clientes', ${c.id})">Excluir</button>
            </div>`,
        },
    ], clientes, { vazio: 'Nenhum cliente cadastrado.' })}</div>`;
}

async function formCliente(id) {
    const cliente = id ? await API.get(`/clientes/${id}`) : {};
    abrirModal(id ? 'Editar cliente' : 'Novo cliente', `
        <form class="formulario" onsubmit="salvarCliente(event, ${id || 'null'})">
            <div class="linha-form">
                ${campo('Nome', 'nome', cliente.nome || '', 'text', 'required')}
                ${campo('Telefone', 'telefone', cliente.telefone || '')}
                ${campo('E-mail', 'email', cliente.email || '', 'email')}
            </div>
            ${areaTexto('Observações', 'observacoes', cliente.observacoes || '')}
            <div class="rodape-modal">
                <button type="button" onclick="fecharModal()">Cancelar</button>
                <button type="submit" class="primario">Salvar</button>
            </div>
        </form>`);
}

async function salvarCliente(evento, id) {
    evento.preventDefault();
    const dados = dadosFormulario(evento.target);
    await comErro(() => (id ? API.put(`/clientes/${id}`, dados) : API.post('/clientes', dados)), 'Cliente salvo.');
    fecharModal();
    recarregar();
}

// =====================================================================
// FINANCEIRO
// =====================================================================
async function telaFinanceiro(alvo) {
    const inicio = document.getElementById('filtro-inicio')?.value || '';
    const fim = document.getElementById('filtro-fim')?.value || '';

    const [resumo, transacoes, fluxo] = await Promise.all([
        API.get(`/financeiro/resumo${params({ inicio, fim })}`),
        API.get(`/financeiro/transacoes${params({ inicio, fim })}`),
        API.get('/dashboard/fluxo-caixa?meses=6'),
    ]);

    alvo.innerHTML = `
        <div class="filtros">
            <div><label>De</label><input type="date" id="filtro-inicio" value="${inicio}"></div>
            <div><label>Até</label><input type="date" id="filtro-fim" value="${fim}"></div>
            <button onclick="recarregar()">Filtrar</button>
        </div>

        <div class="grade grade-kpi" style="margin-bottom:14px">
            <div class="card kpi"><div class="rotulo">Entradas</div><div class="valor positivo">${moeda(resumo.receitas)}</div></div>
            <div class="card kpi"><div class="rotulo">Saídas</div><div class="valor negativo">${moeda(resumo.despesas)}</div></div>
            <div class="card kpi destaque"><div class="rotulo">Saldo</div>
                <div class="valor ${resumo.saldo >= 0 ? 'positivo' : 'negativo'}">${moeda(resumo.saldo)}</div></div>
        </div>

        <div class="grade grade-2" style="margin-bottom:14px">
            <div class="card">
                <h3>Entradas por mês</h3>
                ${graficoBarras(fluxo)}
            </div>
            <div class="card">
                <h3>Por categoria</h3>
                ${barrasHorizontais(
                    resumo.por_categoria.map((c) => ({ label: `${c.tipo === 'despesa' ? '−' : '+'} ${c.categoria}`, valor: c.total })),
                    moeda)}
            </div>
        </div>

        <div class="card">
            <h3>Lançamentos</h3>
            ${tabela([
                { titulo: 'Data', render: (t) => dataCurta(t.data_transacao) },
                { titulo: 'Descrição', render: (t) => escapar(t.descricao) },
                { titulo: 'Categoria', render: (t) => escapar(t.categoria) },
                { titulo: 'Tipo', render: (t) => etiqueta(t.tipo === 'receita' ? 'ok' : 'baixo', t.tipo === 'receita' ? 'entrada' : 'saída') },
                { titulo: 'Valor', num: true, render: (t) => moeda(t.valor) },
                { titulo: 'Status', render: (t) => etiqueta(t.status) },
                {
                    titulo: '', render: (t) => `<div class="acoes-linha">
                        <button class="pequeno perigo" onclick="excluirTransacao(${t.id})">Excluir</button>
                    </div>`,
                },
            ], transacoes, { vazio: 'Nenhum lançamento no período.' })}
        </div>`;
}

function formTransacao() {
    abrirModal('Novo lançamento', `
        <form class="formulario" onsubmit="salvarTransacao(event)">
            <div class="linha-form">
                ${selecao('Tipo', 'tipo', [['despesa', 'Saída / despesa'], ['receita', 'Entrada / receita']])}
                ${campo('Descrição', 'descricao', '', 'text', 'required')}
                ${campo('Valor (R$)', 'valor', '', 'number', 'step="0.01" min="0" required')}
            </div>
            <div class="linha-form">
                ${campo('Categoria', 'categoria', 'geral')}
                ${campo('Data', 'data_transacao', hojeISO(), 'date')}
                ${selecao('Status', 'status', [['pago', 'Pago'], ['pendente', 'Pendente']])}
            </div>
            ${areaTexto('Observações', 'observacoes')}
            <div class="rodape-modal">
                <button type="button" onclick="fecharModal()">Cancelar</button>
                <button type="submit" class="primario">Salvar</button>
            </div>
        </form>`);
}

async function salvarTransacao(evento) {
    evento.preventDefault();
    await comErro(() => API.post('/financeiro/transacoes', dadosFormulario(evento.target)), 'Lançamento salvo.');
    fecharModal();
    recarregar();
}

async function excluirTransacao(id) {
    if (!confirm('Excluir este lançamento?')) return;
    await comErro(() => API.del(`/financeiro/transacoes/${id}`), 'Lançamento excluído.');
    recarregar();
}

// =====================================================================
// CONFIGURAÇÕES
// =====================================================================
async function telaConfiguracoes(alvo) {
    const configs = await API.get('/configuracoes');
    const grupos = [...new Set(configs.map((c) => c.grupo))];

    alvo.innerHTML = grupos.map((grupo) => `
        <div class="card" style="margin-bottom:14px">
            <h3>${escapar(grupo)}</h3>
            <div class="formulario">
                ${configs.filter((c) => c.grupo === grupo).map((c) => `
                    <div class="carrinho-linha">
                        <span class="nome">
                            ${escapar(c.descricao || c.chave)}
                            <br><small style="color:var(--texto-fraco)">${escapar(c.chave)}</small>
                        </span>
                        <input style="width:220px" id="cfg-${c.chave}" value="${escapar(c.valor || '')}">
                        <button class="pequeno primario" onclick="salvarConfig('${c.chave}')">Salvar</button>
                    </div>`).join('')}
            </div>
        </div>`).join('');
}

async function salvarConfig(chave) {
    const valor = document.getElementById(`cfg-${chave}`).value;
    await comErro(() => API.put(`/configuracoes/${chave}`, { valor }), 'Configuração salva.');
    carregarIdentidade();
}

// =====================================================================
// NAVEGAÇÃO
// =====================================================================
const TELAS = {
    dashboard: { titulo: 'Dashboard', render: telaDashboard, acoes: () => '' },
    pdv: { titulo: 'Nova venda', render: telaPdv, acoes: () => '' },
    vendas: { titulo: 'Vendas', render: telaVendas, acoes: () => `<button class="primario" onclick="irPara('pdv')">+ Nova venda</button>` },
    produtos: { titulo: 'Produtos', render: telaProdutos, acoes: () => `<button class="primario" onclick="formProduto()">+ Novo produto</button>` },
    receitas: { titulo: 'Receitas', render: telaReceitas, acoes: () => `<button class="primario" onclick="formReceita()">+ Nova receita</button>` },
    ingredientes: { titulo: 'Ingredientes', render: telaIngredientes, acoes: () => `<button class="primario" onclick="formIngrediente()">+ Novo ingrediente</button>` },
    estoque: { titulo: 'Estoque', render: telaEstoque, acoes: () => `<a class="botao" href="/api/relatorios/estoque.xlsx">⬇ Excel</a>` },
    clientes: { titulo: 'Clientes', render: telaClientes, acoes: () => `<button class="primario" onclick="formCliente()">+ Novo cliente</button>` },
    financeiro: { titulo: 'Financeiro', render: telaFinanceiro, acoes: () => `<button class="primario" onclick="formTransacao()">+ Lançamento</button>` },
    configuracoes: { titulo: 'Configurações', render: telaConfiguracoes, acoes: () => '' },
};

async function irPara(nome) {
    telaAtual = nome;
    const tela = TELAS[nome];

    document.querySelectorAll('.nav-item').forEach((b) => b.classList.toggle('ativo', b.dataset.tela === nome));
    document.getElementById('titulo-tela').textContent = tela.titulo;
    document.getElementById('acoes-tela').innerHTML = tela.acoes();

    const alvo = document.getElementById('tela');
    alvo.innerHTML = '<div class="vazio">Carregando...</div>';
    try {
        await tela.render(alvo);
    } catch (e) {
        alvo.innerHTML = `<div class="card"><div class="vazio">Não deu para carregar: ${escapar(e.message)}</div></div>`;
    }
}

const recarregar = () => irPara(telaAtual);

async function carregarIdentidade() {
    try {
        const configs = await API.get('/configuracoes?grupo=empresa');
        const nome = configs.find((c) => c.chave === 'empresa_nome')?.valor;
        const slogan = configs.find((c) => c.chave === 'empresa_slogan')?.valor;
        if (nome) {
            document.getElementById('empresa-nome').textContent = nome;
            document.title = `ERP ${nome}`;
        }
        if (slogan) document.getElementById('empresa-slogan').textContent = slogan;
    } catch { /* sem configurações cadastradas ainda */ }
}

async function verificarApi() {
    const status = document.getElementById('status-api');
    try {
        const saude = await API.get('/health');
        status.textContent = `● banco ${saude.banco}`;
        status.className = 'status-api ok';
    } catch {
        status.textContent = '● banco indisponível';
        status.className = 'status-api erro';
        mostrarAvisoDeConfiguracao();
    }
}

// Sem banco configurado nenhuma tela funciona, então explicamos o que falta
// em vez de deixar só o erro genérico de carregamento.
function mostrarAvisoDeConfiguracao() {
    document.getElementById('tela').innerHTML = `
        <div class="card">
            <h3>Falta conectar o banco de dados</h3>
            <p style="margin-bottom:14px">
                A aplicação está no ar, mas ainda não consegue falar com um PostgreSQL.
                Para colocar o ERP para funcionar:
            </p>
            <ol style="margin-left:18px;line-height:1.9">
                <li>Crie um banco grátis no <a href="https://neon.tech" target="_blank" rel="noopener">Neon</a>
                    e copie a <em>connection string</em> (use a opção <strong>Pooled connection</strong>).</li>
                <li>No SQL Editor do Neon, execute nesta ordem o conteúdo de
                    <code>schema.sql</code>, <code>views.sql</code> e <code>seeds.sql</code>.</li>
                <li>No painel do Vercel, em <strong>Settings → Environment Variables</strong>,
                    crie <code>DATABASE_URL</code> com essa string e publique de novo.</li>
            </ol>
            <p style="margin-top:14px;color:var(--texto-fraco)">
                Rodando na sua máquina, basta preencher <code>DATABASE_URL</code> no arquivo <code>.env</code>.
            </p>
        </div>`;
}

document.getElementById('menu').addEventListener('click', (e) => {
    const botao = e.target.closest('.nav-item');
    if (botao) irPara(botao.dataset.tela);
});

async function excluir(recurso, id) {
    if (!confirm('Confirma a exclusão? Se o registro já tiver movimento, ele só será desativado.')) return;
    await comErro(() => API.del(`/${recurso}/${id}`), 'Registro removido.');
    recarregar();
}

carregarIdentidade();
verificarApi();
irPara('dashboard');
