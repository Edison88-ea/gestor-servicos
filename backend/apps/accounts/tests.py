from django.test import TestCase
from rest_framework.test import APIClient

from .models import Usuario


class FuncionarioAPITests(TestCase):
    def setUp(self):
        self.rh = Usuario.objects.create_user("rh", password="x", papel=Usuario.Papel.RH)
        self.tecnico = Usuario.objects.create_user(
            "joao", password="x", papel=Usuario.Papel.TECNICO, first_name="João"
        )
        self.api = APIClient()

    def test_tecnico_nao_acessa_lista(self):
        self.api.force_authenticate(self.tecnico)
        resp = self.api.get("/api/funcionarios/")
        self.assertEqual(resp.status_code, 403)

    def test_rh_cria_funcionario_com_senha(self):
        self.api.force_authenticate(self.rh)
        resp = self.api.post(
            "/api/funcionarios/",
            {
                "username": "maria",
                "password": "segredo123",
                "first_name": "Maria",
                "papel": "TECNICO",
                "cpf": "111.222.333-44",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        maria = Usuario.objects.get(username="maria")
        self.assertTrue(maria.check_password("segredo123"))
        self.assertEqual(maria.cpf, "111.222.333-44")

    def test_cria_sem_senha_falha(self):
        self.api.force_authenticate(self.rh)
        resp = self.api.post(
            "/api/funcionarios/", {"username": "x", "first_name": "X"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("password", resp.data)

    def test_desligar_inativa_e_mantem_registro(self):
        self.api.force_authenticate(self.rh)
        resp = self.api.delete(f"/api/funcionarios/{self.tecnico.id}/")
        self.assertEqual(resp.status_code, 204)
        self.tecnico.refresh_from_db()
        self.assertFalse(self.tecnico.is_active)
        self.assertIsNotNone(self.tecnico.data_desligamento)

    def test_lista_esconde_inativos_por_padrao(self):
        self.tecnico.is_active = False
        self.tecnico.save(update_fields=["is_active"])
        self.api.force_authenticate(self.rh)
        self.assertEqual(len(self.api.get("/api/funcionarios/").data["results"]), 1)  # só o RH
        com_inativos = self.api.get("/api/funcionarios/?incluir_inativos=1").data["results"]
        self.assertEqual(len(com_inativos), 2)

    def test_funcionario_ve_os_proprios_dados(self):
        self.api.force_authenticate(self.tecnico)
        resp = self.api.get("/api/funcionarios/meu/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["username"], "joao")
