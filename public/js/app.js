            <button class="pequeno primario" onclick="salvarConfig('${c.chave}')">Salvar</button>`;
}

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
                            ${c.em_uso ? '' : '<span class="tag tag-neutra" title="Nenhuma parte do sistema lê esta configuração ainda">sem efeito ainda</span>'}
                            <br><small style="color:var(--texto-fraco)">${escapar(c.chave)}</small>
                        </span>
                        ${controleConfig(c)}
                    </div>`).join('')}
            </div>
        </div>`).join('');
}

async function salvarConfig(chave, valor) {
    const final = valor ?? document.getElementById(`cfg-${chave}`).value;
    try {
        await comErro(() => API.put(`/configuracoes/${chave}`, { valor: final }), 'Configuração salva.');
        carregarIdentidade();
    } catch {
        // comErro ja mostrou o motivo na tela
    }
    // recarrega sempre: apos um erro, o controle volta ao valor que esta gravado
    recarregar();
}

function salvarMeses(chave) {
    const meses = [...document.querySelectorAll(`#cfg-${chave} input:checked`)].map((c) => c.value);
    salvarConfig(chave, meses.join(','));
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
