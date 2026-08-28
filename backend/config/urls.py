from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_media
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.spa import healthz, spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthz),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.clients.urls")),
    path("api/", include("apps.service_orders.urls")),
    path("api/", include("apps.timeclock.urls")),
    path("api/", include("apps.notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # App interno, volume baixo: servir a mídia pelo Django é suficiente nesta
    # fase e evita depender de um bucket/CDN. As fotos e assinaturas ficam no
    # disco do serviço — efêmeras no plano free do Render (ver DEPLOY.md).
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            serve_media,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]

# Catch-all: qualquer rota que não seja API/admin/media/static/healthz entrega
# o index.html do SPA. O WhiteNoise já interceptou os arquivos que existem no
# build (assets, sw.js, manifest, ícones) antes de chegar aqui.
urlpatterns += [
    re_path(r"^(?!api/|admin/|media/|static/|healthz/).*$", spa_index),
]
