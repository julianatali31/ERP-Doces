"""Ponto de entrada do Vercel.

O Vercel procura um objeto ASGI chamado `app` dentro de api/. Aqui so
reaproveitamos a aplicacao FastAPI do pacote app/ - nada de logica nova.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

__all__ = ["app"]
