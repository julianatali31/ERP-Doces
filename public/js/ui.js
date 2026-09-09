const moeda = (v) => (Number(v) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const numero = (v, casas = 2) => (Number(v) || 0).toLocaleString('pt-BR', { maximumFractionDigits: casas });
const pct = (v) => `${(Number(v) || 0).toFixed(1)}%`;
const dataHora = (iso) => new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
const dataCurta = (iso) => new Date(iso + (iso.length === 10 ? 'T12:00:00' : '')).toLocaleDateString('pt-BR');
const hojeISO = () => new Date().toISOString().slice(0, 10);

const escapar = (texto) => String(texto ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
));

function avisar(mensagem, tipo = 'ok') {
    const div = document.createElement('div');
    div.className = `aviso ${tipo}`;
    div.textContent = mensagem;
    document.getElementById('avisos').appendChild(div);
    setTimeout(() => div.remove(), 3800);
}

async function comErro(acao, mensagemSucesso) {
    try {
        const resultado = await acao();
        if (mensagemSucesso) avisar(mensagemSucesso);
        return resultado;
    } catch (e) {
        avisar(e.message, 'erro');
        throw e;
    }
}

function abrirModal(titulo, html) {
    document.getElementById('modal-titulo').textContent = titulo;
    document.getElementById('modal-corpo').innerHTML = html;
    document.getElementById('modal-fundo').hidden = false;
}

function fecharModal() {
    document.getElementById('modal-fundo').hidden = true;
    document.getElementById('modal-corpo').innerHTML = '';
}

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') fecharModal(); });
document.addEventListener('click', (e) => {
    if (e.target.id === 'modal-fundo') fecharModal();
});

function campo(rotulo, nome, valor = '', tipo = 'text', extra = '') {
    return `<div>
        <label for="f-${nome}">${rotulo}</label>
        <input id="f-${nome}" name="${nome}" type="${tipo}" value="${escapar(valor)}" ${extra}>
    </div>`;
}

function selecao(rotulo, nome, opcoes, selecionado = '', extra = '') {
    const itens = opcoes.map(([v, t]) =>
        `<option value="${escapar(v)}" ${String(v) === String(selecionado) ? 'selected' : ''}>${escapar(t)}</option>`
    ).join('');
    return `<div>
        <label for="f-${nome}">${rotulo}</label>
        <select id="f-${nome}" name="${nome}" ${extra}>${itens}</select>
    </div>`;
}

function areaTexto(rotulo, nome, valor = '') {
    return `<div style="grid-column: 1 / -1">
        <label for="f-${nome}">${rotulo}</label>
        <textarea id="f-${nome}" name="${nome}">${escapar(valor)}</textarea>
    </div>`;
}

function dadosFormulario(formulario) {
    const dados = {};
    new FormData(formulario).forEach((valor, chave) => {
        dados[chave] = typeof valor === 'string' ? valor.trim() : valor;
    });
    formulario.querySelectorAll('input[type=checkbox]').forEach((c) => { dados[c.name] = c.checked; });
    formulario.querySelectorAll('input[type=number]').forEach((c) => {
        dados[c.name] = c.value === '' ? null : Number(c.value);
    });
    Object.keys(dados).forEach((k) => { if (dados[k] === '') dados[k] = null; });
    return dados;
}

function tabela(colunas, linhas, opcoes = {}) {
    if (!linhas.length) return `<div class="vazio">${opcoes.vazio || 'Nada por aqui ainda.'}</div>`;
    const cabecalho = colunas.map((c) => `<th class="${c.num ? 'num' : ''}">${c.titulo}</th>`).join('');
    const corpo = linhas.map((linha) =>
        `<tr>${colunas.map((c) => `<td class="${c.num ? 'num' : ''}">${c.render(linha)}</td>`).join('')}</tr>`
    ).join('');
    return `<div class="tabela-area"><table><thead><tr>${cabecalho}</tr></thead><tbody>${corpo}</tbody></table></div>`;
}

function graficoBarras(dados, formatar = moeda) {
    if (!dados.length) return '<div class="vazio">Sem dados no período.</div>';
    const maximo = Math.max(...dados.map((d) => d.valor), 1);
    const colunas = dados.map((d) => `
        <div class="barra-col">
            <div class="barra-area">
                <div class="barra" style="height:${(d.valor / maximo) * 100}%" data-valor="${formatar(d.valor)}"></div>
            </div>
            <span class="barra-rotulo">${escapar(d.label)}</span>
        </div>`).join('');
    return `<div class="grafico-barras">${colunas}</div>`;
}

function barrasHorizontais(dados, formatar = numero) {
    if (!dados.length) return '<div class="vazio">Sem dados ainda.</div>';
    const maximo = Math.max(...dados.map((d) => d.valor), 1);
    return dados.map((d) => `
        <div class="barra-horizontal">
            <span class="nome" title="${escapar(d.label)}">${escapar(d.label)}</span>
            <div class="trilho"><div class="preenchido" style="width:${(d.valor / maximo) * 100}%"></div></div>
            <span class="num">${formatar(d.valor)}</span>
        </div>`).join('');
}

const etiqueta = (valor, texto) => `<span class="tag tag-${valor}">${escapar(texto ?? valor)}</span>`;
