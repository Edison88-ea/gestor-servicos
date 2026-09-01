from datetime import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.clients.models import Cliente
from apps.notifications.models import Notificacao

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


class EncarregadoTests(TestCase):
    def setUp(self):
        self.encarregado = Usuario.objects.create_user(
            username="enc", password="x", papel=Usuario.Papel.ENCARREGADO
        )
        self.auxiliar = Usuario.objects.create_user(
            username="aux", password="x", papel=Usuario.Papel.TECNICO,
            encarregado_responsavel=self.encarregado,
        )
        self.outro = Usuario.objects.create_user(
            username="outro", password="x", papel=Usuario.Papel.TECNICO
        )
        self.cliente = Cliente.objects.create(nome="ACME")
        self.api = APIClient()

    def _os(self, tecnico):
        return OrdemServico.objects.create(
            cliente=self.cliente, tecnico=tecnico, criado_por=tecnico, tipo_servico="X"
        )

    def test_encarregado_ve_as_proprias_e_as_da_equipe_mas_nao_as_de_fora(self):
        minha = self._os(self.encarregado)
        do_aux = self._os(self.auxiliar)
        de_fora = self._os(self.outro)

        self.api.force_authenticate(self.encarregado)
        ids = {o["id"] for o in self.api.get("/api/ordens-servico/").data["results"]}
        self.assertEqual(ids, {minha.id, do_aux.id})
        self.assertNotIn(de_fora.id, ids)

    def test_auxiliar_continua_vendo_so_as_proprias(self):
        do_aux = self._os(self.auxiliar)
        self._os(self.encarregado)
        self.api.force_authenticate(self.auxiliar)
        ids = {o["id"] for o in self.api.get("/api/ordens-servico/").data["results"]}
        self.assertEqual(ids, {do_aux.id})

    def test_encarregado_abre_os_e_ela_fica_atribuida_a_ele(self):
        self.api.force_authenticate(self.encarregado)
        resp = self.api.post(
            "/api/ordens-servico/",
            {"cliente": self.cliente.id, "tipo_servico": "Manutenção"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["tecnico"], self.encarregado.id)

    def test_encarregado_pode_criar_obra(self):
        self.api.force_authenticate(self.encarregado)
        resp = self.api.post("/api/projetos/", {"nome": "Obra do encarregado"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_painel_so_para_gestao(self):
        self.api.force_authenticate(self.auxiliar)
        self.assertEqual(self.api.get("/api/painel/").status_code, 403)

        gestor = Usuario.objects.create_user(username="pg", password="x", papel=Usuario.Papel.GESTOR)
        self._os(self.auxiliar)
        self.api.force_authenticate(gestor)
        resp = self.api.get("/api/painel/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("os_abertas", resp.data["kpis"])
        self.assertGreaterEqual(resp.data["kpis"]["os_abertas"], 1)

    def test_conclusao_notifica_encarregado_e_gestor_menos_o_autor(self):
        gestor = Usuario.objects.create_user(
            username="g", password="x", papel=Usuario.Papel.GESTOR
        )
        os = self._os(self.auxiliar)
        self.api.force_authenticate(self.auxiliar)
        resp = self.api.post(f"/api/ordens-servico/{os.id}/concluir/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)

        avisados = set(
            Notificacao.objects.filter(tipo=Notificacao.Tipo.OS_CONCLUIDA).values_list(
                "destinatario_id", flat=True
            )
        )
        self.assertEqual(avisados, {self.encarregado.id, gestor.id})
        self.assertNotIn(self.auxiliar.id, avisados)
