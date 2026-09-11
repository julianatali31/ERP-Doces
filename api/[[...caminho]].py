"""Ponto de entrada do Vercel.

O Vercel procura um objeto ASGI chamado `app` dentro de api/. Aqui so
reaproveitamos a aplicacao FastAPI do pacote app/ - nada de logica nova.

Se a importacao falhar, servimos no lugar dela uma aplicacao minima que
devolve o motivo do erro. Sem isso a funcao morre antes de responder e o
navegador mostra apenas "FUNCTION_INVOCATION_FAILED", sem dizer o que houve -
e a causa fica so no log da hospedagem, que nem sempre esta ao alcance.
"""

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from app.main import app  # noqa: E402
except Exception as erro:  # noqa: BLE001 - qualquer falha aqui precisa virar resposta
    _causa = f"{type(erro).__name__}: {erro}"
    print(traceback.format_exc(), file=sys.stderr)

    from fastapi import FastAPI  # noqa: E402
    from fastapi.responses import JSONResponse  # noqa: E402

    app = FastAPI(title="ERP - falha na inicializacao")

    @app.get("/api/health")
    async def health_indisponivel():
        return JSONResponse(
            status_code=503,
            content={
                "status": "erro",
                "banco": "indisponivel",
                "detalhe": f"A aplicacao nao iniciou. {_causa}",
            },
        )

    @app.api_route("/{caminho:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def falha_na_inicializacao(caminho: str):
        return JSONResponse(
            status_code=503,
            content={"erro": "A aplicacao nao conseguiu iniciar.", "causa": _causa},
        )

__all__ = ["app"]
