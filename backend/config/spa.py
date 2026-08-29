"""Servir o SPA (Vue) e um health check simples a partir do Django.

Em produção o frontend buildado (frontend/dist) é servido pelo mesmo serviço:
os arquivos estáticos saem pelo WhiteNoise e qualquer rota "de tela" cai aqui,
devolvendo o index.html para o Vue Router assumir no cliente.
"""

import mimetypes
import os
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.views.decorators.cache import cache_control, never_cache


@never_cache
def healthz(request):
    """Usado pelo health check do Render. Inclui o commit para saber qual
    versão está no ar (o Render injeta RENDER_GIT_COMMIT)."""
    return JsonResponse(
        {
            "status": "ok",
            "commit": os.environ.get("RENDER_GIT_COMMIT", "")[:7],
        }
    )


@cache_control(private=True, max_age=60 * 60 * 24 * 7)
def serve_media(request, path):
    """Serve um arquivo de MEDIA a partir do storage padrão (disco local em dev,
    bucket R2 em produção). Manter isto na API — em vez de expor o bucket ou
    usar URL assinada — deixa as URLs /media/... estáveis e na mesma origem, o
    que o service worker do PWA já sabe cachear para uso offline."""
    if not path or path.endswith("/") or ".." in path:
        raise Http404
    try:
        arquivo = default_storage.open(path)
    except (FileNotFoundError, OSError):
        raise Http404
    tipo = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return FileResponse(arquivo, content_type=tipo)


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
