from datetime import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.clients.models import Cliente

from .models import OrdemServico


class ExportacaoComprovanteTests(TestCase):
    def setUp(self):
        self.gestor = Usuario.objects.create_user(
            username="gestor", password="x", papel=Usuario.Papel.GESTOR
        )
        self.tec = Usuario.objects.create_user(
            username="tec", password="x", papel=Usuario.Papel.TECNICO
        )
        self.cliente = Cliente.objects.create(nome="ACME", documento="123", telefone="9999")
        self.api = APIClient()
        self.api.force_authenticate(self.gestor)

    def _os_concluida(self, quando):
        return OrdemServico.objects.create(
            cliente=self.cliente,
            tecnico=self.tec,
            criado_por=self.gestor,
            tipo_servico="Manutenção",
            status=OrdemServico.Status.CONCLUIDA,
            data_conclusao=timezone.make_aware(quando),
        )

    def test_serializer_traz_dados_do_cliente_para_o_comprovante(self):
        os = self._os_concluida(datetime(2026, 8, 10, 15, 0))
        resp = self.api.get(f"/api/ordens-servico/{os.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["cliente_detalhe"]["documento"], "123")
        self.assertEqual(resp.data["criado_por_nome"], self.gestor.get_full_name())

    def test_filtro_por_mes_de_conclusao(self):
        self._os_concluida(datetime(2026, 8, 10, 15, 0))
        self._os_concluida(datetime(2026, 7, 2, 9, 0))
        resp = self.api.get("/api/ordens-servico/?status=CONCLUIDA&concluida_mes=2026-08")
        self.assertEqual(resp.data["count"], 1)

    def test_page_size_maior_que_o_padrao(self):
        for d in range(1, 26):
            self._os_concluida(datetime(2026, 8, d, 12, 0))
        resp = self.api.get("/api/ordens-servico/?status=CONCLUIDA&page_size=500")
        self.assertEqual(len(resp.data["results"]), 25)
