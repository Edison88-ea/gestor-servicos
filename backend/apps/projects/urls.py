from rest_framework.routers import DefaultRouter

from .views import EtapaViewSet, ProjetoViewSet

router = DefaultRouter()
router.register("projetos", ProjetoViewSet, basename="projeto")
router.register("etapas", EtapaViewSet, basename="etapa")

urlpatterns = router.urls
