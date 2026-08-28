"""Servir o SPA (Vue) e um health check simples a partir do Django.

Em produção o frontend buildado (frontend/dist) é servido pelo mesmo serviço:
os arquivos estáticos saem pelo WhiteNoise e qualquer rota "de tela" cai aqui,
devolvendo o index.html para o Vue Router assumir no cliente.
"""

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def healthz(request):
    """Usado pelo health check do Render."""
    return JsonResponse({"status": "ok"})


@never_cache
def spa_index(request):
    index = Path(settings.FRONTEND_DIST) / "index.html"
    if not index.is_file():
        return HttpResponse(
            "Frontend ainda não foi buildado (frontend/dist/index.html não existe).",
            status=503,
            content_type="text/plain; charset=utf-8",
        )
    return HttpResponse(index.read_bytes(), content_type="text/html; charset=utf-8")
