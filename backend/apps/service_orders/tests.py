import io
from datetime import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.clients.models import Cliente
from apps.notifications.models import Notificacao
from config.uploads import MAX_MB_IMAGEM

from .models import FotoOrdemServico, OrdemServico


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

    def test_painel_tecnico_sem_acesso_gestor_e_encarregado_com(self):
        self.api.force_authenticate(self.outro)  # técnico solto
        self.assertEqual(self.api.get("/api/painel/").status_code, 403)

        gestor = Usuario.objects.create_user(username="pg", password="x", papel=Usuario.Papel.GESTOR)
        self._os(self.auxiliar)
        self.api.force_authenticate(gestor)
        resp = self.api.get("/api/painel/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.data["kpis"]["os_abertas"], 1)
        self.assertTrue(resp.data["e_gestao"])

        # encarregado: só a equipe dele
        self._os(self.outro)  # OS de fora
        self.api.force_authenticate(self.encarregado)
        resp = self.api.get("/api/painel/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["e_gestao"])
        nomes_equipe = {m["nome"] for m in resp.data["equipe"]}
        self.assertIn(self.auxiliar.get_full_name() or "aux", nomes_equipe)
        self.assertNotIn("outro", nomes_equipe)

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

    def test_reconcluir_edita_sem_mexer_em_status_data_nem_notificar(self):
        Usuario.objects.create_user(username="g2", password="x", papel=Usuario.Papel.GESTOR)
        os = self._os(self.auxiliar)
        self.api.force_authenticate(self.auxiliar)
        self.api.post(f"/api/ordens-servico/{os.id}/concluir/", {}, format="json")

        os.refresh_from_db()
        concluida_em = os.data_conclusao
        n_avisos = Notificacao.objects.filter(tipo=Notificacao.Tipo.OS_CONCLUIDA).count()

        resp = self.api.post(
            f"/api/ordens-servico/{os.id}/concluir/",
            {"relato": {"local": "Sala 2", "servicos": ["troca de disjuntor"]}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)

        os.refresh_from_db()
        self.assertEqual(os.status, OrdemServico.Status.CONCLUIDA)
        self.assertEqual(os.data_conclusao, concluida_em)  # data original preservada
        self.assertIn("troca de disjuntor", os.observacoes_tecnico)
        self.assertEqual(
            Notificacao.objects.filter(tipo=Notificacao.Tipo.OS_CONCLUIDA).count(),
            n_avisos,  # nenhum aviso novo
        )

    def test_tecnico_nao_exclui_os_gestor_sim(self):
        os = self._os(self.auxiliar)
        self.api.force_authenticate(self.auxiliar)
        self.assertEqual(self.api.delete(f"/api/ordens-servico/{os.id}/").status_code, 403)
        gestor = Usuario.objects.create_user("gx", password="x", papel=Usuario.Papel.GESTOR)
        self.api.force_authenticate(gestor)
        self.assertEqual(self.api.delete(f"/api/ordens-servico/{os.id}/").status_code, 204)

    def test_tecnico_nao_troca_cliente_de_os_concluida(self):
        outro_cliente = Cliente.objects.create(nome="Outro")
        os = self._os(self.auxiliar)
        self.api.force_authenticate(self.auxiliar)
        self.api.post(f"/api/ordens-servico/{os.id}/concluir/", {}, format="json")
        resp = self.api.patch(
            f"/api/ordens-servico/{os.id}/", {"cliente": outro_cliente.id}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        os.refresh_from_db()
        self.assertEqual(os.cliente_id, self.cliente.id)


def _jpeg(lado=40, cor=(120, 130, 140)):
    buf = io.BytesIO()
    Image.new("RGB", (lado, lado), cor).save(buf, format="JPEG")
    return buf.getvalue()


class UploadHardeningTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.gestor = Usuario.objects.create_user(
            username="g", password="x", papel=Usuario.Papel.GESTOR
        )
        self.cliente = Cliente.objects.create(nome="ACME", documento="1", telefone="9")
        self.api.force_authenticate(self.gestor)
        self.os = OrdemServico.objects.create(
            cliente=self.cliente, criado_por=self.gestor, tipo_servico="X"
        )

    def _post_foto(self, conteudo, nome="foto.jpg", tipo="image/jpeg"):
        arquivo = SimpleUploadedFile(nome, conteudo, content_type=tipo)
        return self.api.post(
            f"/api/ordens-servico/{self.os.id}/fotos/",
            {"imagem": arquivo},
            format="multipart",
        )

    def test_foto_valida_passa_e_e_comprimida(self):
        resp = self._post_foto(_jpeg(), nome="camera.png")
        self.assertEqual(resp.status_code, 201)
        foto = FotoOrdemServico.objects.get()
        # save() re-encoda para .jpg
        self.assertTrue(foto.imagem.name.endswith(".jpg"))

    def test_imagem_acima_do_limite_e_rejeitada(self):
        gordo = _jpeg() + b"\x00" * ((MAX_MB_IMAGEM + 1) * 1024 * 1024)
        resp = self._post_foto(gordo)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("muito grande", str(resp.data).lower())
        self.assertEqual(FotoOrdemServico.objects.count(), 0)

    def test_decompression_bomb_de_imagem_e_rejeitada(self):
        from PIL import Image as PILImage

        original = PILImage.MAX_IMAGE_PIXELS
        PILImage.MAX_IMAGE_PIXELS = 100  # 10x10 já estoura
        try:
            resp = self._post_foto(_jpeg(lado=50))
        finally:
            PILImage.MAX_IMAGE_PIXELS = original
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(FotoOrdemServico.objects.count(), 0)

    def test_middleware_corta_content_length_gigante(self):
        from django.http import HttpResponse
        from django.test import RequestFactory

        from config.uploads import LimiteTamanhoRequisicaoMiddleware

        mw = LimiteTamanhoRequisicaoMiddleware(lambda r: HttpResponse("ok"))

        grande = RequestFactory().post("/api/ordens-servico/1/fotos/")
        grande.META["CONTENT_LENGTH"] = str(50 * 1024 * 1024)
        self.assertEqual(mw(grande).status_code, 413)

        ok = RequestFactory().post("/api/ordens-servico/1/fotos/")
        ok.META["CONTENT_LENGTH"] = str(2 * 1024 * 1024)
        self.assertEqual(mw(ok).status_code, 200)

        get = RequestFactory().get("/qualquer")
        self.assertEqual(mw(get).status_code, 200)
