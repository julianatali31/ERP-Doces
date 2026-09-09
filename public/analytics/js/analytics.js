/* Tela de analytics de vendas.
 *
 * Consome os endpoints novos de /api/analytics e, para a série diária, o
 * /api/dashboard/vendas-por-dia que já existia — nada é recalculado aqui.
 *
 * Os formatadores são locais de propósito: ui.js registra listeners de modal
 * que esta página não tem, então importar o arquivo inteiro traria peso e
 * comportamento que não se aplicam.
 */

const moeda = (v) => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const numero = (v) => (Number(v) || 0).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
const iso = (d) => d.toISOString().slice(0, 10);
const diasEntre = (de, ate) => Math.round((ate - de) / 86400000);

const CORES = {
    roxo: '#7c3aed',
    roxoClaro: '#a78bfa',
    verde: '#10b981',
    vermelho: '#ef4444',
    ambar: '#f59e0b',
    texto: '#ececf1',
    textoFraco: '#9b9bab',
    borda: '#2a2a3a',
};

Chart.defaults.color = CORES.textoFraco;
Chart.defaults.borderColor = CORES.borda;
Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";

const graficos = {};
let granularidade = 'semana';

/** Cria ou atualiza um gráfico, evitando canvas duplicado a cada refiltragem. */
function desenhar(id, config) {
    if (graficos[id]) graficos[id].destroy();
    graficos[id] = new Chart(document.getElementById(id), config);
}

function periodoSelecionado() {
    return {
        inicio: document.getElementById('filtro-inicio').value,
        fim: document.getElementById('filtro-fim').value,
    };
}

// ------------------------------------------------------------------ cartões
function cartao(titulo, valor, indicador, formatador) {
    const v = indicador.variacao_pct;
    let classe = 'neutra';
    let texto = 'sem base de comparação';

    if (v !== null && v !== undefined) {
        classe = v > 0 ? 'sobe' : (v < 0 ? 'desce' : 'neutra');
        const seta = v > 0 ? '▲' : (v < 0 ? '▼' : '—');
        texto = `${seta} ${Math.abs(v).toFixed(1)}% <small>vs ${formatador(indicador.anterior)}</small>`;
    }

    return `
        <div class="cartao">
            <div class="cartao-titulo">${titulo}</div>
            <div class="cartao-valor">${valor}</div>
            <div class="variacao ${classe}">${texto}</div>
        </div>`;
}

async function carregarCartoes() {
    const alvo = document.getElementById('cartoes');
    const dados = await API.get(`/analytics/comparativo${params(periodoSelecionado())}`);

    alvo.innerHTML = [
        cartao('Faturamento', moeda(dados.faturamento.atual), dados.faturamento, moeda),
        cartao('Lucro', moeda(dados.lucro.atual), dados.lucro, moeda),
        cartao('Vendas', numero(dados.vendas.atual), dados.vendas, numero),
        cartao('Ticket médio', moeda(dados.ticket_medio.atual), dados.ticket_medio, moeda),
    ].join('');

    return dados;
}

// ------------------------------------------------------------- faturamento
/** Série diária: usa o endpoint que já existe e recorta o intervalo pedido.
 *
 * O /dashboard/vendas-por-dia devolve os últimos N dias terminando hoje, então
 * o recorte é por índice — a série é contígua, um ponto por dia.
 */
async function serieDiaria(inicio, fim) {
    const hoje = new Date(iso(new Date()));
    const de = new Date(inicio);
    const ate = new Date(fim);

    const dias = Math.min(diasEntre(de, hoje) + 1, 365);
    if (dias < 1) return { pontos: [], truncada: false };

    const serie = await API.get(`/dashboard/vendas-por-dia?dias=${dias}`);
    const sobra = Math.max(diasEntre(ate, hoje), 0);
    const pontos = sobra > 0 ? serie.slice(0, Math.max(serie.length - sobra, 0)) : serie;

    return {
        pontos: pontos.map((p) => ({ periodo: p.label, faturamento: p.valor, lucro: p.valor_secundario })),
        truncada: diasEntre(de, hoje) + 1 > 365,
    };
}

async function carregarFaturamento() {
    const { inicio, fim } = periodoSelecionado();
    let pontos;
    let aviso = '';

    if (granularidade === 'dia') {
        const resultado = await serieDiaria(inicio, fim);
        pontos = resultado.pontos;
        if (resultado.truncada) aviso = 'Série diária limitada aos últimos 365 dias.';
    } else {
        pontos = await API.get(`/analytics/faturamento${params({ granularidade, inicio, fim })}`);
    }

    desenhar('gr-faturamento', {
        type: 'bar',
        data: {
            labels: pontos.map((p) => p.periodo),
            datasets: [
                {
                    label: 'Faturamento',
                    data: pontos.map((p) => p.faturamento),
                    backgroundColor: CORES.roxo,
                    borderRadius: 5,
                },
                {
                    label: 'Lucro',
                    type: 'line',
                    data: pontos.map((p) => p.lucro),
                    borderColor: CORES.verde,
                    backgroundColor: CORES.verde,
                    tension: 0.3,
                    pointRadius: pontos.length > 40 ? 0 : 3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { boxWidth: 12 } },
                tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${moeda(c.parsed.y)}` } },
            },
            scales: {
                y: { beginAtZero: true, ticks: { callback: (v) => moeda(v) } },
                x: { grid: { display: false } },
            },
        },
    });

    document.querySelector('#gr-faturamento').closest('.card').dataset.aviso = aviso;
}

// ---------------------------------------------------------------- produtos
async function carregarProdutos() {
    const { inicio, fim } = periodoSelecionado();
    const linhas = await API.get(`/analytics/produtos${params({ inicio, fim, limite: 8 })}`);

    desenhar('gr-produtos', {
        type: 'bar',
        data: {
            labels: linhas.map((l) => l.produto),
            datasets: [{
                label: 'Unidades vendidas',
                data: linhas.map((l) => l.unidades),
                backgroundColor: CORES.roxoClaro,
                borderRadius: 5,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: (c) => `${numero(c.parsed.x)} unidades` } },
            },
            scales: { x: { beginAtZero: true }, y: { grid: { display: false } } },
        },
    });

    const tabela = document.getElementById('tabela-produtos');
    if (!linhas.length) {
        tabela.innerHTML = '<tbody><tr><td class="vazio-inline">Sem vendas no período.</td></tr></tbody>';
        return;
    }

    tabela.innerHTML = `
        <thead><tr><th>Produto</th><th>Faturamento</th><th>% do total</th></tr></thead>
        <tbody>
            ${linhas.map((l) => `
                <tr>
                    <td>${l.produto}</td>
                    <td>${moeda(l.faturamento)}</td>
                    <td>${l.participacao_pct.toFixed(1)}%</td>
                </tr>`).join('')}
        </tbody>`;
}

// ------------------------------------------------------------ sazonalidade
async function carregarSazonalidade() {
    const meses = await API.get('/analytics/sazonalidade?anos=3');
    const comDados = meses.filter((m) => m.anos_com_dados > 0);

    desenhar('gr-sazonalidade', {
        type: 'bar',
        data: {
            labels: meses.map((m) => m.nome.slice(0, 3)),
            datasets: [{
                label: 'Faturamento médio',
                data: meses.map((m) => m.faturamento_medio),
                // Recesso em âmbar para a queda saltar aos olhos.
                backgroundColor: meses.map((m) => (m.recesso ? CORES.ambar : CORES.roxo)),
                borderRadius: 5,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (c) => {
                            const m = meses[c.dataIndex];
                            const sufixo = m.recesso ? ' · recesso' : '';
                            return `${moeda(m.faturamento_medio)} · ${m.vendas} vendas${sufixo}`;
                        },
                    },
                },
            },
            scales: {
                y: { beginAtZero: true, ticks: { callback: (v) => moeda(v) } },
                x: { grid: { display: false } },
            },
        },
    });

    const nota = document.getElementById('nota-sazonalidade');
    const recesso = meses.filter((m) => m.recesso && m.anos_com_dados > 0);
    const normais = comDados.filter((m) => !m.recesso);

    if (recesso.length && normais.length) {
        const mediaRecesso = recesso.reduce((s, m) => s + m.faturamento_medio, 0) / recesso.length;
        const mediaNormal = normais.reduce((s, m) => s + m.faturamento_medio, 0) / normais.length;
        const queda = mediaNormal ? (1 - mediaRecesso / mediaNormal) * 100 : 0;
        nota.textContent =
            `No recesso (${recesso.map((m) => m.nome).join(', ')}) o faturamento médio é ` +
            `${moeda(mediaRecesso)}, contra ${moeda(mediaNormal)} nos demais meses — ` +
            `uma queda de ${queda.toFixed(0)}%.`;
    } else {
        nota.textContent = comDados.length
            ? 'Defina os meses de recesso em Configurações → meses_recesso para destacá-los aqui.'
            : 'Ainda não há vendas suficientes para desenhar a sazonalidade.';
    }
}

// -------------------------------------------------------------- orquestração
async function atualizar() {
    const status = document.getElementById('status-api');
    try {
        await Promise.all([
            carregarCartoes(),
            carregarFaturamento(),
            carregarProdutos(),
            carregarSazonalidade(),
        ]);
        status.textContent = '● dados atualizados';
        status.className = 'status-api ok';
    } catch (erro) {
        status.textContent = `● ${erro.message}`;
        status.className = 'status-api erro';
        document.getElementById('cartoes').innerHTML =
            `<div class="vazio-inline">Não foi possível carregar: ${erro.message}</div>`;
    }
}

function definirPeriodo(dias) {
    const hoje = new Date();
    const de = new Date(hoje);
    de.setDate(de.getDate() - (dias - 1));
    document.getElementById('filtro-inicio').value = iso(de);
    document.getElementById('filtro-fim').value = iso(hoje);
}

document.addEventListener('DOMContentLoaded', () => {
    definirPeriodo(90);

    document.getElementById('filtro-inicio').addEventListener('change', atualizar);
    document.getElementById('filtro-fim').addEventListener('change', atualizar);

    document.getElementById('atalhos').addEventListener('click', (e) => {
        const botao = e.target.closest('.atalho');
        if (!botao) return;
        definirPeriodo(Number(botao.dataset.dias));
        atualizar();
    });

    document.getElementById('granularidade').addEventListener('click', (e) => {
        const botao = e.target.closest('button');
        if (!botao) return;
        granularidade = botao.dataset.gran;
        document.querySelectorAll('#granularidade button')
            .forEach((b) => b.classList.toggle('ativo', b === botao));
        carregarFaturamento();
    });

    atualizar();
});
