from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.spa import healthz, serve_media, spa_index

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
    path("api/", include("apps.projects.urls")),
]

# Mídia (fotos/assinaturas) servida pela API a partir do storage padrão — disco
# local em dev, bucket R2 em produção. Ver config.spa.serve_media e DEPLOY.md.
urlpatterns += [
    re_path(r"^media/(?P<path>.+)$", serve_media, name="serve_media"),
]

# Catch-all: qualquer rota que não seja API/admin/media/static/healthz entrega
# o index.html do SPA. O WhiteNoise já interceptou os arquivos que existem no
# build (assets, sw.js, manifest, ícones) antes de chegar aqui.
urlpatterns += [
    re_path(r"^(?!api/|admin/|media/|static/|healthz/).*$", spa_index),
]
