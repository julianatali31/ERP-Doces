"""Data e hora no fuso do negocio.

O servidor roda em UTC (na Vercel e no Neon). Para a confeitaria, "hoje" e
"o dia da venda" sao do horario do Brasil: uma venda as 21h do dia 6 e do dia
6, nao do dia 7. Toda conta de data feita em Python passa por aqui.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import settings

FUSO = ZoneInfo(settings.fuso_horario)


def agora() -> datetime:
    return datetime.now(FUSO)


def hoje() -> date:
    return agora().date()


def local(momento: datetime) -> datetime:
    """Converte um instante para o fuso do negocio.

    Datas sem fuso vindas do banco sao tratadas como UTC, que e como o
    PostgreSQL guarda timestamptz.
    """
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=ZoneInfo("UTC"))
    return momento.astimezone(FUSO)
