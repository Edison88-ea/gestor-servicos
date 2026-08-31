import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import Usuario

from .models import AssinaturaProjeto, Etapa, Projeto


def imagem_falsa(nome="assinatura.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(nome, buffer.getvalue(), content_type="image/png")


class ProjetoModelTests(TestCase):
    def test_numero_sequencial_e_progresso(self):
        p1 = Projeto.objects.create(nome="Volkswagen")
        p2 = Projeto.objects.create(nome="Patagonia - Alternador")
        self.assertEqual(p1.numero, "PRJ000001")
        self.assertEqual(p2.numero, "PRJ000002")

        Etapa.objects.create(projeto=p1, nome="Rede", meta=4, realizado=1)
        Etapa.objects.create(projeto=p1, nome="Ar", meta=6, realizado=4)
        # 5 de 10 = 50%
        self.assertEqual(p1.progresso, 50)
        self.assertEqual(p1.total_meta, 10)
        self.assertEqual(p1.total_realizado, 5)

    def test_progresso_sem_etapa_e_zero(self):
        self.assertEqual(Projeto.objects.create(nome="Vazio").progresso, 0)


class ProjetoAPITests(TestCase):
    def setUp(self):
        self.gestor = Usuario.objects.create_user(
            username="gestor", password="x", papel=Usuario.Papel.GESTOR
        )
        self.tec = Usuario.objects.create_user(
            username="tec", password="x", papel=Usuario.Papel.TECNICO
        )
        self.api = APIClient()

    def test_tecnico_nao_cria_projeto(self):
        self.api.force_authenticate(self.tec)
        resp = self.api.post("/api/projetos/", {"nome": "X"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_gestor_cria_projeto_com_areas_validadas(self):
        self.api.force_authenticate(self.gestor)
        resp = self.api.post(
            "/api/projetos/",
            {"nome": "Volks", "areas_afetadas": ["VOLKS", "ADM"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["numero"], "PRJ000001")
        self.assertEqual(resp.data["criado_por_nome"], self.gestor.get_full_name())

        ruim = self.api.post(
            "/api/projetos/", {"nome": "Y", "areas_afetadas": ["INEXISTENTE"]}, format="json"
        )
        self.assertEqual(ruim.status_code, 400)

    def test_opcoes_traz_catalogos(self):
        self.api.force_authenticate(self.tec)
        resp = self.api.get("/api/projetos/opcoes/")
        self.assertEqual(resp.status_code, 200)
        codigos = {a["valor"] for a in resp.data["areas_afetadas"]}
        self.assertIn("LOGISTICA", codigos)
        self.assertTrue(resp.data["tipos_ponto"])


class EtapaProgressoTests(TestCase):
    def setUp(self):
        self.gestor = Usuario.objects.create_user(
            username="gestor", password="x", papel=Usuario.Papel.GESTOR
        )
        self.tec = Usuario.objects.create_user(
            username="tec", password="x", papel=Usuario.Papel.TECNICO
        )
        self.projeto = Projeto.objects.create(nome="Volks")
        self.etapa = Etapa.objects.create(projeto=self.projeto, nome="Rede", meta=5)
        self.api = APIClient()

    def test_tecnico_atualiza_progresso_gera_historico_e_faz_clamp(self):
        self.api.force_authenticate(self.tec)
        resp = self.api.post(
            f"/api/etapas/{self.etapa.id}/progresso/",
            {"realizado": 99, "observacao": "instalados hoje"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.etapa.refresh_from_db()
        self.assertEqual(self.etapa.realizado, 5)  # clamp na meta
        hist = self.etapa.historico.get()
        self.assertEqual((hist.quantidade_anterior, hist.quantidade_nova), (0, 5))
        self.assertEqual(hist.usuario, self.tec)

    def test_progresso_igual_nao_gera_historico(self):
        self.api.force_authenticate(self.tec)
        self.api.post(f"/api/etapas/{self.etapa.id}/progresso/", {"realizado": 0}, format="json")
        self.assertEqual(self.etapa.historico.count(), 0)

    def test_tecnico_nao_edita_meta(self):
        self.api.force_authenticate(self.tec)
        resp = self.api.patch(
            f"/api/etapas/{self.etapa.id}/", {"meta": 100}, format="json"
        )
        self.assertEqual(resp.status_code, 403)


class AssinaturaProjetoTests(TestCase):
    def setUp(self):
        self.tec = Usuario.objects.create_user(
            username="tec", password="x", papel=Usuario.Papel.TECNICO
        )
        self.projeto = Projeto.objects.create(nome="Volks")
        self.api = APIClient()
        self.api.force_authenticate(self.tec)

    def test_tecnico_coleta_assinatura_em_campo(self):
        resp = self.api.post(
            f"/api/projetos/{self.projeto.id}/assinaturas/",
            {
                "papel": AssinaturaProjeto.Papel.SUPERVISOR,
                "nome": "Cristiano Almeida",
                "assinatura": imagem_falsa(),
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["papel_display"], "Supervisor de processos")
        self.assertEqual(self.projeto.assinaturas.count(), 1)
