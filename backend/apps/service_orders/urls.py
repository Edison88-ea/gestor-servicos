from rest_framework.routers import DefaultRouter

from .views import (
    MaterialCatalogoViewSet,
    OrdemServicoViewSet,
    ServicoCatalogoViewSet,
)

router = DefaultRouter()
router.register("ordens-servico", OrdemServicoViewSet, basename="ordem-servico")
router.register("catalogo/servicos", ServicoCatalogoViewSet, basename="catalogo-servico")
router.register("catalogo/materiais", MaterialCatalogoViewSet, basename="catalogo-material")

urlpatterns = router.urls
