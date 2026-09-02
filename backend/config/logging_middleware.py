"""Loga cada chamada da API: método, caminho, status, duração e usuário.

Sai no console do runserver e no arquivo backend/logs/api.log (ver LOGGING no
settings). Para chamadas que falham (4xx/5xx) também registra o corpo da
resposta, que é onde costuma estar a mensagem de erro.

Exceção: rotas com dado pessoal sensível (ficha de funcionário) nunca têm o
corpo da resposta nem a query string gravados — CPF, salário, dados bancários
etc. não podem parar num arquivo de log ou no stdout do Render.
"""

import logging
import time

logger = logging.getLogger("api")

CORPO_MAX = 1000

# Prefixos cujo corpo/query não vão pro log (só método, caminho e status).
ROTAS_SENSIVEIS = ("/api/funcionarios",)


class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        inicio = time.monotonic()
        resposta = self.get_response(request)
        ms = int((time.monotonic() - inicio) * 1000)

        user = getattr(request, "user", None)
        quem = user.get_username() if user and user.is_authenticated else "anon"

        sensivel = request.path.startswith(ROTAS_SENSIVEIS)
        caminho = request.path if sensivel else request.get_full_path()
        linha = f"{request.method} {caminho} → {resposta.status_code} ({ms}ms) [{quem}]"

        if resposta.status_code >= 400 and not sensivel:
            corpo = getattr(resposta, "content", b"")[:CORPO_MAX].decode("utf-8", "replace")
            logger.warning("%s  %s", linha, corpo)
        elif resposta.status_code >= 400:
            logger.warning(linha)
        else:
            logger.info(linha)

        return resposta
