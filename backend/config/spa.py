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


# Tipos que podem ser exibidos inline com segurança. Qualquer outra coisa que
# um usuário tenha subido (HTML/SVG com script, etc.) é forçada a download —
# senão /media/x.html executaria JS na origem do app e roubaria o token do
# localStorage.
_MEDIA_INLINE_OK = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
}


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
    inline = tipo in _MEDIA_INLINE_OK
    resposta = FileResponse(
        arquivo,
        content_type=tipo if inline else "application/octet-stream",
        as_attachment=not inline,
    )
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta


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
