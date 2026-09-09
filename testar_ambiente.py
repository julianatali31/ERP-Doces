"""
Diagnostico do ambiente - ERP Dom Cookies

Verifica, em ordem, tudo que precisa estar de pe para o sistema funcionar, e
para no primeiro problema dizendo exatamente o que fazer.

Como usar (com o venv ativado, na pasta do projeto):
    python testar_ambiente.py
"""
import asyncio
import socket
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

RAIZ = Path(__file__).resolve().parent
LARGURA = 64


def titulo(numero, texto):
    print()
    print("=" * LARGURA)
    print(f"TESTE {numero}: {texto}")
    print("=" * LARGURA)


def ok(texto):
    print(f"  [OK]     {texto}")


def falhar(texto, *instrucoes):
    print(f"  [FALHOU] {texto}")
    if instrucoes:
        print()
        print("  Como resolver:")
        for linha in instrucoes:
            print(f"    {linha}")
    print()
    sys.exit(1)


# --------------------------------------------------------------- 1. pacotes
titulo(1, "Pacotes instalados")

for modulo, nome in [
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("sqlalchemy", "SQLAlchemy"),
    ("asyncpg", "AsyncPG"),
    ("pydantic", "Pydantic"),
    ("dotenv", "python-dotenv"),
]:
    try:
        __import__(modulo)
        ok(nome)
    except ImportError:
        falhar(
            f"{nome} nao esta instalado.",
            "Confirme que o venv esta ativado (deve aparecer '(venv)' no",
            "inicio da linha do terminal). Se nao aparecer:",
            "    Windows : venv\\Scripts\\activate",
            "    Linux   : source venv/bin/activate",
            "Depois:",
            "    pip install -r requirements.txt",
        )

# ------------------------------------------------------------------ 2. .env
titulo(2, "Arquivo .env")

from dotenv import load_dotenv  # noqa: E402  (so faz sentido apos o teste 1)
import os  # noqa: E402

if not (RAIZ / ".env").exists():
    falhar(
        "Nao existe um arquivo .env na pasta do projeto.",
        "Crie um a partir do exemplo:",
        "    Windows : copy .env.example .env",
        "    Linux   : cp .env.example .env",
        "Depois abra o .env e preencha a senha do seu PostgreSQL.",
    )

load_dotenv(RAIZ / ".env")
url = os.getenv("DATABASE_URL")

if not url:
    falhar(
        "O .env existe, mas nao tem DATABASE_URL.",
        "Adicione uma linha assim (trocando SENHA pela sua):",
        "    DATABASE_URL=postgresql+asyncpg://postgres:SENHA@localhost:5432/erp_confeitaria",
    )

partes = urlsplit(url.replace("postgresql+asyncpg://", "postgresql://"))
host = partes.hostname or "localhost"
porta = partes.port or 5432
usuario = unquote(partes.username or "postgres")
senha = unquote(partes.password or "")
banco = (partes.path or "/").lstrip("/") or "postgres"

ok(f"DATABASE_URL lida: {usuario}@{host}:{porta}/{banco}")
if not senha:
    print("  [AVISO]  A URL nao tem senha. Se o seu PostgreSQL exigir uma, o")
    print("           proximo teste vai falhar na autenticacao.")

# ---------------------------------------------------- 3. servidor alcancavel
titulo(3, f"PostgreSQL respondendo em {host}:{porta}")

try:
    with socket.create_connection((host, porta), timeout=5):
        ok("A porta esta aberta - o servidor esta de pe.")
except OSError as erro:
    falhar(
        f"Nada respondeu em {host}:{porta} ({erro}).",
        "Isso quase sempre e uma destas tres coisas:",
        "",
        "1. O PostgreSQL nao esta rodando. Inicie o servico:",
        "     Windows : Servicos > postgresql-x64-16 > Iniciar",
        "     Linux   : sudo systemctl start postgresql",
        "",
        f"2. Ele esta rodando em outra porta (o .env pede {porta}).",
        "   A porta padrao e 5432. Confira no pgAdmin, em Properties >",
        "   Connection, e ajuste a porta no .env se for diferente.",
        "",
        "3. O host esta errado. Para banco na sua maquina, use localhost.",
    )

# --------------------------------------------------- 4. autenticacao e banco
titulo(4, "Login e banco de dados")


async def conectar():
    import asyncpg

    try:
        return await asyncpg.connect(
            host=host, port=porta, user=usuario, password=senha, database=banco
        )
    except Exception as erro:
        texto = str(erro).lower()
        if "password" in texto or "authentication" in texto:
            falhar(
                f"Usuario ou senha recusados para '{usuario}'.",
                "A senha do .env precisa ser a mesma que voce usa no pgAdmin.",
                "Se nao lembrar, redefina no terminal do PostgreSQL:",
                "    ALTER USER postgres PASSWORD 'sua_nova_senha';",
                "e atualize a linha DATABASE_URL do .env.",
                "",
                "Atencao: senha com @ ou : na URL precisa ser codificada.",
                "Ex.: 'a@b' vira 'a%40b'.",
            )
        if "does not exist" in texto and banco in texto:
            falhar(
                f"O servidor respondeu, mas o banco '{banco}' nao existe.",
                "Crie o banco e carregue a estrutura, nesta ordem:",
                f"    createdb -U {usuario} {banco}",
                f"    psql -U {usuario} -d {banco} -f schema.sql",
                f"    psql -U {usuario} -d {banco} -f views.sql",
                f"    psql -U {usuario} -d {banco} -f seeds.sql",
                "",
                "Pelo pgAdmin: clique com o botao direito em Databases >",
                f"Create > Database, chame de '{banco}', e depois use a Query",
                "Tool para rodar os tres arquivos .sql na ordem acima.",
            )
        falhar(f"Nao foi possivel conectar. Detalhe: {erro}")


# -------------------------------------------------------------- 5. estrutura
# Conexao e consultas ficam no mesmo asyncio.run(): o asyncpg amarra a conexao
# ao event loop onde ela nasceu, e usar outro loop depois quebra.
async def checar_banco():
    conn = await conectar()
    ok(f"Conectado em '{banco}' como '{usuario}'.")

    titulo(5, "Estrutura do banco (tabelas, views e funcoes)")

    tabelas = {
        "configuracoes", "categorias", "clientes", "ingredientes", "receitas",
        "receita_ingredientes", "produtos", "vendas", "venda_itens",
        "movimentacao_estoque", "transacoes_financeiras",
    }
    existentes = {
        r["table_name"]
        for r in await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
    }

    faltando = sorted(tabelas - existentes)
    if faltando:
        falhar(
            f"Faltam {len(faltando)} tabela(s): {', '.join(faltando)}",
            "O schema.sql nao foi carregado (ou foi carregado pela metade).",
            f"    psql -U {usuario} -d {banco} -f schema.sql",
        )
    ok(f"{len(tabelas)} tabelas encontradas.")

    views = {
        r["table_name"]
        for r in await conn.fetch(
            "SELECT table_name FROM information_schema.views WHERE table_schema='public'"
        )
    }
    if "vw_dashboard_kpis" not in views:
        falhar(
            "As views nao existem - o views.sql nao foi carregado.",
            "Este e o erro mais confuso do projeto: a API sobe normalmente,",
            "mas toda tela quebra, porque o dashboard le das views.",
            f"    psql -U {usuario} -d {banco} -f views.sql",
        )
    ok(f"{len(views)} views encontradas.")

    funcao = await conn.fetchval(
        "SELECT COUNT(*) FROM pg_proc WHERE proname = 'calcular_custo_receita'"
    )
    if not funcao:
        falhar(
            "A funcao calcular_custo_receita() nao existe.",
            "Sem ela os custos ficam zerados. Recarregue o schema:",
            f"    psql -U {usuario} -d {banco} -f schema.sql",
        )
    ok("Funcoes e triggers de calculo no lugar.")

    # ---------------------------------------------------------- 6. dados
    titulo(6, "Dados cadastrados")

    ingredientes = await conn.fetchval("SELECT COUNT(*) FROM ingredientes")
    receitas = await conn.fetchval("SELECT COUNT(*) FROM receitas")
    produtos = await conn.fetchval("SELECT COUNT(*) FROM produtos")

    if not ingredientes:
        falhar(
            "O banco esta vazio - o seeds.sql nao foi carregado.",
            f"    psql -U {usuario} -d {banco} -f seeds.sql",
        )

    empresa = await conn.fetchval(
        "SELECT valor FROM configuracoes WHERE chave = 'empresa_nome'"
    )
    print(f"  Empresa      : {empresa or '(nao configurado)'}")
    print(f"  Ingredientes : {ingredientes}")
    print(f"  Receitas     : {receitas}")
    print(f"  Produtos     : {produtos}")

    zerados = await conn.fetchval(
        "SELECT COUNT(*) FROM receitas r WHERE r.custo_total = 0"
        " AND EXISTS (SELECT 1 FROM receita_ingredientes ri WHERE ri.receita_id = r.id)"
    )
    if zerados:
        print()
        print(f"  [AVISO]  {zerados} receita(s) com ingredientes mas custo zerado.")
        print("           Os triggers nao rodaram nesses registros. Para recalcular:")
        print("           UPDATE receitas SET atualizado_em = NOW();")

    await conn.close()


asyncio.run(checar_banco())

# ------------------------------------------------------------- 7. frontend
titulo(7, "Arquivos da interface")

esperados = [
    "public/index.html",
    "public/css/style.css",
    "public/js/api.js",
    "public/js/app.js",
    "public/js/ui.js",
]
ausentes = [c for c in esperados if not (RAIZ / c).exists()]

if ausentes:
    falhar(
        f"Faltam arquivos da interface: {', '.join(ausentes)}",
        "A API sobe, mas o navegador mostra 404 ou tela em branco.",
        "Confirme que voce esta na pasta certa do projeto e que o",
        "repositorio foi baixado por completo (git status deve estar limpo).",
    )
ok(f"{len(esperados)} arquivos da interface no lugar.")

print()
print("=" * LARGURA)
print("TUDO CERTO. Suba o sistema com:")
print("    uvicorn app.main:app --reload")
print("e abra http://localhost:8000 no navegador.")
print("=" * LARGURA)
