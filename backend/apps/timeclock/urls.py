from rest_framework.routers import DefaultRouter

from .views import RegistroPontoViewSet, SolicitacaoPontoViewSet

router = DefaultRouter()
router.register("registros-ponto", RegistroPontoViewSet, basename="registro-ponto")
router.register("solicitacoes-ponto", SolicitacaoPontoViewSet, basename="solicitacao-ponto")

urlpatterns = router.urls
