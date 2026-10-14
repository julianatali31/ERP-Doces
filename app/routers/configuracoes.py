from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Configuracao
from app.schemas import ConfiguracaoOut, ConfiguracaoUpdate

router = APIRouter(prefix="/api/configuracoes", tags=["Configuracoes"])

# Como cada configuracao e editada. A tela le isto para desenhar o controle
# certo - interruptor, lista, meses - em vez de um campo de texto livre onde
# era preciso digitar "true" ou "light" a mao.
#
#   editavel=False  so quem administra muda, direto no banco (nao ha login no
#                   sistema, entao a tela simplesmente nao permite)
#   opcoes          valores aceitos; vira uma lista de escolha
#   controle        forca um controle especifico
_REGRAS: dict[str, dict] = {
    "versao": {"editavel": False},
    "tema_padrao": {"opcoes": ["dark", "light"]},
    "moeda": {"opcoes": ["BRL"]},
    "meses_recesso": {"controle": "meses"},
}

# Configuracoes que algum codigo do sistema realmente le. As demais vieram dos
# dados iniciais e ainda nao tem efeito - a tela avisa, para nao parecer que
# ligar o "backup automatico" faz backup.
_EM_USO = {"empresa_nome", "empresa_slogan", "meses_recesso"}

_CONTROLE_POR_TIPO = {"boolean": "interruptor", "number": "numero"}


def _saida(config: Configuracao) -> ConfiguracaoOut:
    regra = _REGRAS.get(config.chave, {})
    editavel = regra.get("editavel", True)
    if not editavel:
        controle = "leitura"
    elif "controle" in regra:
        controle = regra["controle"]
    elif "opcoes" in regra:
        controle = "lista"
    else:
        controle = _CONTROLE_POR_TIPO.get(config.tipo, "texto")

    saida = ConfiguracaoOut.model_validate(config)
    saida.editavel = editavel
    saida.controle = controle
    saida.opcoes = regra.get("opcoes")
    saida.em_uso = config.chave in _EM_USO
    return saida


def _validar(config: Configuracao, valor: str) -> str:
    """Recusa valores que o campo de texto livre deixava passar."""
    regra = _REGRAS.get(config.chave, {})
    valor = valor.strip()

    if not regra.get("editavel", True):
        raise HTTPException(
            403,
            f"'{config.chave}' e definida por quem administra o sistema e nao pode ser alterada pela tela.",
        )
    if "opcoes" in regra and valor not in regra["opcoes"]:
        raise HTTPException(400, f"Valor invalido. Opcoes aceitas: {', '.join(regra['opcoes'])}.")

    if regra.get("controle") == "meses":
        partes = [p.strip() for p in valor.split(",") if p.strip()]
        if any(not p.isdigit() or not 1 <= int(p) <= 12 for p in partes):
            raise HTTPException(400, "Informe os meses como numeros de 1 a 12, separados por virgula.")
        # normaliza: sem repeticao e em ordem, "12,7,7" vira "7,12"
        return ",".join(str(m) for m in sorted({int(p) for p in partes}))

    if config.tipo == "boolean":
        if valor.lower() not in ("true", "false"):
            raise HTTPException(400, "Use true ou false.")
        return valor.lower()
    if config.tipo == "number":
        try:
            float(valor.replace(",", "."))
        except ValueError:
            raise HTTPException(400, "Informe um numero.") from None
        return valor.replace(",", ".")
    return valor


@router.get("", response_model=list[ConfiguracaoOut])
async def listar(grupo: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Configuracao).order_by(Configuracao.grupo, Configuracao.chave)
    if grupo:
        stmt = stmt.where(Configuracao.grupo == grupo)
    return [_saida(c) for c in (await db.execute(stmt)).scalars().all()]


@router.put("/{chave}", response_model=ConfiguracaoOut)
async def atualizar(chave: str, dados: ConfiguracaoUpdate, db: AsyncSession = Depends(get_db)):
    config = (
        await db.execute(select(Configuracao).where(Configuracao.chave == chave))
    ).scalar_one_or_none()
    if not config:

