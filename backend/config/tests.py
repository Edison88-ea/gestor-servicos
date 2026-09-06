from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Usuario


class LogSensivelTests(TestCase):
    """A ficha de funcionário não pode aparecer no api.log."""

    def setUp(self):
        self.rh = Usuario.objects.create_user("rh", password="x", papel=Usuario.Papel.RH)
        self.api = APIClient()
        self.api.force_authenticate(self.rh)

    def test_erro_em_funcionarios_nao_loga_corpo_nem_query(self):
        with self.assertLogs("api", level="INFO") as cap:
            # 400 (sem senha) + CPF na query string
            self.api.post(
                "/api/funcionarios/?search=123.456.789-00",
                {"username": "x", "first_name": "X", "cpf": "123.456.789-00"},
                format="json",
            )
        linhas = "\n".join(cap.output)
        self.assertIn("/api/funcionarios/", linhas)
        self.assertNotIn("123.456.789-00", linhas)  # nem query, nem corpo ecoado
        self.assertNotIn("password", linhas)

    def test_erro_em_outra_rota_ainda_loga_corpo(self):
        # regressão: o log de diagnóstico continua valendo fora das rotas sensíveis
        with self.assertLogs("api", level="INFO") as cap:
            self.api.get("/api/ordens-servico/999999/")
        self.assertIn("/api/ordens-servico/999999/", "\n".join(cap.output))


class ServeMediaTests(TestCase):
    """Arquivo subido não pode renderizar inline na origem do app (XSS)."""

    def _get_media(self, nome, conteudo):
        caminho = default_storage.save(nome, ContentFile(conteudo))
        resp = self.client.get(f"/media/{caminho}")
        b"".join(resp.streaming_content)  # consome
        resp.close()
        default_storage.delete(caminho)
        return resp

    def test_html_e_forcado_a_download(self):
        resp = self._get_media("teste/x.html", b"<script>alert(1)</script>")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("text/html", resp["Content-Type"])
        self.assertIn("attachment", resp.get("Content-Disposition", ""))
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")

    def test_imagem_continua_inline(self):
        resp = self._get_media("teste/x.png", b"\x89PNG\r\n\x1a\n fake")
        self.assertEqual(resp["Content-Type"], "image/png")
        self.assertNotIn("attachment", resp.get("Content-Disposition", ""))

    def test_path_traversal_bloqueado(self):
        from config.spa import serve_media
        from django.http import Http404
        from django.test import RequestFactory

        req = RequestFactory().get("/media/x")
        with self.assertRaises(Http404):
            serve_media(req, "../settings.py")
