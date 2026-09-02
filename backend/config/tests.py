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
