from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Usuario
from apps.clients.models import Cliente
from apps.service_orders.models import MaterialCatalogo, OrdemServico

from .models import Material, MovimentoEstoque
from .movimentos import aplicar_entrada, parse_quantidade, sincronizar_saida_os


class ParseQuantidadeTests(TestCase):
    def test_casos(self):
        self.assertEqual(parse_quantidade("10"), Decimal("10"))
        self.assertEqual(parse_quantidade("10,5 m"), Decimal("10.5"))
        self.assertEqual(parse_quantidade("15 m"), Decimal("15"))
        self.assertIsNone(parse_quantidade("3x2,5"))
        self.assertIsNone(parse_quantidade(""))
        self.assertIsNone(parse_quantidade(None))
        self.assertIsNone(parse_quantidade("uma caixa"))
        self.assertIsNone(parse_quantidade("0"))


class MovimentoLogicaTests(TestCase):
    def setUp(self):
        self.mat = Material.objects.create(descricao="Cabo PP 3x2,5 mm²", unidade="m")

    def test_entrada_soma_saldo_e_faz_media_ponderada(self):
        aplicar_entrada(self.mat, Decimal("100"), custo_unitario=Decimal("2.00"))
        self.mat.refresh_from_db()
        self.assertEqual(self.mat.saldo, Decimal("100.000"))
        self.assertEqual(self.mat.custo_unitario, Decimal("2.00"))

        aplicar_entrada(self.mat, Decimal("100"), custo_unitario=Decimal("4.00"))
        self.mat.refresh_from_db()
        self.assertEqual(self.mat.saldo, Decimal("200.000"))
        # (100*2 + 100*4) / 200 = 3.00
        self.assertEqual(self.mat.custo_unitario, Decimal("3.00"))

    def test_ajuste_define_saldo_absoluto(self):
        aplicar_entrada(self.mat, Decimal("50"))
        from .movimentos import aplicar_ajuste

        aplicar_ajuste(self.mat, Decimal("12"), observacao="inventário")
        self.mat.refresh_from_db()
        self.assertEqual(self.mat.saldo, Decimal("12.000"))
        ultimo = self.mat.movimentos.first()
        self.assertEqual(ultimo.tipo, MovimentoEstoque.Tipo.AJUSTE)
        self.assertEqual(ultimo.saldo_apos, Decimal("12.000"))

    def test_saida_pode_ficar_negativa(self):
        from .movimentos import aplicar_saida

        aplicar_saida(self.mat, Decimal("5"))
        self.mat.refresh_from_db()
        self.assertEqual(self.mat.saldo, Decimal("-5.000"))
        self.assertTrue(self.mat.saldo < 0)


class BaixaAutomaticaOSTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nome="ACME", documento="1", telefone="9")
        self.gestor = Usuario.objects.create_user(
            username="g", password="x", papel=Usuario.Papel.GESTOR
        )
        self.perfilado = Material.objects.create(descricao="Perfilado", unidade="un")
        aplicar_entrada(self.perfilado, Decimal("50"))

    def _os(self):
        return OrdemServico.objects.create(
            cliente=self.cliente,
            criado_por=self.gestor,
            tipo_servico="Infra",
            status=OrdemServico.Status.CONCLUIDA,
            data_conclusao=timezone.now(),
        )

    def test_baixa_material_cadastrado_com_qtd_numerica(self):
        os = self._os()
        relato = {
            "materiais": [
                {"descricao": "Perfilado", "quantidade": "6", "unidade": "un"},
                {"descricao": "Cabo PP 3x2,5", "quantidade": "10 m", "unidade": "m"},
            ]
        }
        res = sincronizar_saida_os(os, relato, usuario=self.gestor)
        self.perfilado.refresh_from_db()
        self.assertEqual(self.perfilado.saldo, Decimal("44.000"))
        self.assertEqual(len(res["baixados"]), 1)
        self.assertEqual(len(res["ignorados"]), 1)  # Cabo PP não é item de estoque

    def test_qtd_nao_numerica_nao_baixa(self):
        os = self._os()
        relato = {"materiais": [{"descricao": "Perfilado", "quantidade": "alguns"}]}
        res = sincronizar_saida_os(os, relato, usuario=self.gestor)
        self.perfilado.refresh_from_db()
        self.assertEqual(self.perfilado.saldo, Decimal("50.000"))
        self.assertEqual(res["ignorados"][0]["motivo"], "quantidade não numérica")

    def test_reconcluir_nao_duplica_baixa(self):
        os = self._os()
        relato = {"materiais": [{"descricao": "Perfilado", "quantidade": "6"}]}
        sincronizar_saida_os(os, relato, usuario=self.gestor)
        sincronizar_saida_os(os, relato, usuario=self.gestor)
        sincronizar_saida_os(os, relato, usuario=self.gestor)
        self.perfilado.refresh_from_db()
        self.assertEqual(self.perfilado.saldo, Decimal("44.000"))
        self.assertEqual(
            MovimentoEstoque.objects.filter(
                ordem_servico=os, tipo=MovimentoEstoque.Tipo.SAIDA
            ).count(),
            1,
        )

    def test_editar_relato_ajusta_baixa(self):
        os = self._os()
        sincronizar_saida_os(
            os, {"materiais": [{"descricao": "Perfilado", "quantidade": "6"}]}
        )
        sincronizar_saida_os(
            os, {"materiais": [{"descricao": "Perfilado", "quantidade": "10"}]}
        )
        self.perfilado.refresh_from_db()
        self.assertEqual(self.perfilado.saldo, Decimal("40.000"))


class APITests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.gestor = Usuario.objects.create_user(
            username="g", password="x", papel=Usuario.Papel.GESTOR
        )
        self.tec = Usuario.objects.create_user(
            username="t", password="x", papel=Usuario.Papel.TECNICO
        )

    def test_tecnico_le_mas_nao_cria(self):
        self.api.force_authenticate(self.tec)
        self.assertEqual(self.api.get("/api/materiais-estoque/").status_code, 200)
        resp = self.api.post("/api/materiais-estoque/", {"descricao": "Fita"})
        self.assertEqual(resp.status_code, 403)

    def test_gestor_cria_com_saldo_inicial(self):
        self.api.force_authenticate(self.gestor)
        resp = self.api.post(
            "/api/materiais-estoque/",
            {"descricao": "Keystone", "unidade": "un", "saldo_inicial": "20", "custo_inicial": "8.50"},
        )
        self.assertEqual(resp.status_code, 201)
        mat = Material.objects.get(descricao="Keystone")
        self.assertEqual(mat.saldo, Decimal("20.000"))
        self.assertEqual(mat.custo_unitario, Decimal("8.50"))
        self.assertEqual(mat.movimentos.count(), 1)

    def test_entrada_e_ajuste_via_api(self):
        self.api.force_authenticate(self.gestor)
        mat = Material.objects.create(descricao="Tomada steck 220V", unidade="un")
        r1 = self.api.post(
            f"/api/materiais-estoque/{mat.id}/entrada/",
            {"quantidade": "30", "custo_unitario": "12", "documento": "NF 123"},
        )
        self.assertEqual(r1.status_code, 201)
        r2 = self.api.post(
            f"/api/materiais-estoque/{mat.id}/ajuste/",
            {"saldo_contado": "28", "observacao": "quebrou 2"},
        )
        self.assertEqual(r2.status_code, 201)
        mat.refresh_from_db()
        self.assertEqual(mat.saldo, Decimal("28.000"))

    def test_filtro_abaixo_minimo(self):
        self.api.force_authenticate(self.gestor)
        baixo = Material.objects.create(descricao="Baixo", estoque_minimo=Decimal("10"))
        aplicar_entrada(baixo, Decimal("3"))
        Material.objects.create(descricao="Ok", estoque_minimo=Decimal("1"), saldo=Decimal("5"))
        resp = self.api.get("/api/materiais-estoque/?abaixo_minimo=1")
        descricoes = [m["descricao"] for m in resp.data["results"]]
        self.assertEqual(descricoes, ["Baixo"])

    def test_do_catalogo_cria_itens(self):
        self.api.force_authenticate(self.gestor)
        MaterialCatalogo.objects.get_or_create(
            descricao="Curva de perfilado", defaults={"unidade_padrao": "un", "usos": 4}
        )
        MaterialCatalogo.objects.get_or_create(
            descricao="Emenda de perfilado", defaults={"unidade_padrao": "un", "usos": 3}
        )
        pendentes = self.api.get("/api/materiais-estoque/do-catalogo/")
        nomes = {p["descricao"] for p in pendentes.data}
        self.assertIn("Curva de perfilado", nomes)
        self.assertIn("Emenda de perfilado", nomes)
        criados = self.api.post(
            "/api/materiais-estoque/do-catalogo/", {"descricoes": ["Curva de perfilado"]}, format="json"
        )
        self.assertEqual(criados.status_code, 201)
        self.assertTrue(Material.objects.filter(descricao="Curva de perfilado").exists())
        self.assertFalse(Material.objects.filter(descricao="Emenda de perfilado").exists())


class ConclusaoOSIntegracaoTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.gestor = Usuario.objects.create_user(
            username="g", password="x", papel=Usuario.Papel.GESTOR
        )
        self.cliente = Cliente.objects.create(nome="ACME", documento="1", telefone="9")
        self.api.force_authenticate(self.gestor)
        self.mat = Material.objects.create(descricao="Perfilado", unidade="un")
        aplicar_entrada(self.mat, Decimal("50"))

    def test_concluir_os_baixa_estoque(self):
        os = OrdemServico.objects.create(
            cliente=self.cliente, criado_por=self.gestor, tipo_servico="Infra"
        )
        resp = self.api.post(
            f"/api/ordens-servico/{os.id}/concluir/",
            {"relato": {"materiais": [{"descricao": "Perfilado", "quantidade": "8"}]}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("baixa_estoque", resp.data)
        self.mat.refresh_from_db()
        self.assertEqual(self.mat.saldo, Decimal("42.000"))
