from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import Usuario

from .models import Cliente


class ClientePermissaoTests(TestCase):
    def setUp(self):
        self.tec = Usuario.objects.create_user("t", password="x", papel=Usuario.Papel.TECNICO)
        self.gestor = Usuario.objects.create_user("g", password="x", papel=Usuario.Papel.GESTOR)
        self.cliente = Cliente.objects.create(nome="ACME")
        self.api = APIClient()

    def test_tecnico_le_e_cadastra_mas_nao_edita_nem_exclui(self):
        self.api.force_authenticate(self.tec)
        self.assertEqual(self.api.get("/api/clientes/").status_code, 200)
        self.assertEqual(
            self.api.post("/api/clientes/", {"nome": "Nova"}, format="json").status_code, 201
        )
        self.assertEqual(
            self.api.patch(f"/api/clientes/{self.cliente.id}/", {"nome": "X"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.api.delete(f"/api/clientes/{self.cliente.id}/").status_code, 403)

    def test_gestor_edita_e_exclui(self):
        self.api.force_authenticate(self.gestor)
        self.assertEqual(
            self.api.patch(f"/api/clientes/{self.cliente.id}/", {"nome": "X"}, format="json").status_code,
            200,
        )
