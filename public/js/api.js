const API = {
    async pedir(caminho, opcoes = {}) {
        const resposta = await fetch(`/api${caminho}`, {
            headers: { 'Content-Type': 'application/json' },
            ...opcoes,
            body: opcoes.corpo ? JSON.stringify(opcoes.corpo) : undefined,
        });

        if (!resposta.ok) {
            let detalhe = `Erro ${resposta.status}`;
            try {
                const erro = await resposta.json();
                if (typeof erro.detail === 'string') detalhe = erro.detail;
                else if (Array.isArray(erro.detail)) detalhe = erro.detail.map(e => e.msg).join(', ');
            } catch { /* resposta sem corpo JSON */ }
            throw new Error(detalhe);
        }

        return resposta.status === 204 ? null : resposta.json();
    },

    get(caminho) { return this.pedir(caminho); },
    post(caminho, corpo) { return this.pedir(caminho, { method: 'POST', corpo }); },
    put(caminho, corpo) { return this.pedir(caminho, { method: 'PUT', corpo }); },
    del(caminho) { return this.pedir(caminho, { method: 'DELETE' }); },
};

const params = (obj) => {
    const q = new URLSearchParams();
    Object.entries(obj).forEach(([chave, valor]) => {
        if (valor !== null && valor !== undefined && valor !== '') q.append(chave, valor);
    });
    const s = q.toString();
    return s ? `?${s}` : '';
};
