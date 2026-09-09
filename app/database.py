import os
from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# Rodando como funcao serverless (Vercel): cada invocacao e um processo curto,
# entao manter um pool aberto so acumula conexoes mortas no banco.
SEM_ESTADO = bool(os.getenv("VERCEL"))

# Parametros que o asyncpg nao aceita na URL - servicos como Neon e Supabase
# os incluem na string que aparece no painel.
_PARAMS_IGNORADOS = {"sslmode", "channel_binding", "options", "target_session_attrs"}


def preparar_url(url: str) -> tuple[str, dict]:
    """Aceita a string de conexao como ela vem do painel do provedor.

    Converte para o driver assincrono, tira os parametros que o asyncpg nao
    entende e liga o SSL quando o banco nao e local.
    """
    for prefixo in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if url.startswith(prefixo):
            url = "postgresql+asyncpg://" + url[len(prefixo):]
            break

    partes = urlsplit(url)
    consulta = [(c, v) for c, v in parse_qsl(partes.query) if c not in _PARAMS_IGNORADOS]
    url_limpa = urlunsplit(partes._replace(query=urlencode(consulta)))

    local = (partes.hostname or "") in ("localhost", "127.0.0.1", "::1")
    return url_limpa, ({} if local else {"ssl": "require"})


url_banco, argumentos_conexao = preparar_url(settings.database_url)

engine = create_async_engine(
    url_banco,
    echo=False,
    connect_args=argumentos_conexao,
    **(
        {"poolclass": NullPool}
        if SEM_ESTADO
        else {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}
    ),
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
