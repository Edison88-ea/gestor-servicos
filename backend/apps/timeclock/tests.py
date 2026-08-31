from datetime import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import Usuario

from .models import RegistroPonto, SolicitacaoPonto
from .views import _agrupar_jornadas, _calcular_dias, validar_sequencia_ponto

_T = RegistroPonto.Tipo


def _m(ano, mes, dia, h, mi=0):
    return timezone.make_aware(datetime(ano, mes, dia, h, mi))


class ValidarSequenciaPontoTests(TestCase):
    def setUp(self):
        self.func = Usuario.objects.create_user(username="tec", password="x")

    def _reg(self, tipo, quando):
        RegistroPonto.objects.create(funcionario=self.func, tipo=tipo, registrado_em=quando)

    def test_saida_de_madrugada_fecha_entrada_da_noite_anterior(self):
        """O bug do print: Entrada domingo 19h, Saída segunda 00:21."""
        self._reg(_T.ENTRADA, _m(2026, 8, 30, 19, 0))
        # não deve levantar
        validar_sequencia_ponto(self.func, _T.SAIDA, _m(2026, 8, 31, 0, 21))

    def test_saida_intervalo_atrasada_valida_apos_saida_ja_salva(self):
        self._reg(_T.ENTRADA, _m(2026, 8, 29, 8, 0))
        self._reg(_T.SAIDA, _m(2026, 8, 29, 17, 0))
        validar_sequencia_ponto(self.func, _T.SAIDA_INTERVALO, _m(2026, 8, 29, 12, 0))

    def test_entrada_no_dia_seguinte_apos_jornada_esquecida_e_permitida(self):
        # Entrada segunda 08h, esqueceu a Saída. Terça 08h bate Entrada de novo.
        self._reg(_T.ENTRADA, _m(2026, 8, 24, 8, 0))
        validar_sequencia_ponto(self.func, _T.ENTRADA, _m(2026, 8, 25, 8, 0))

    def test_batida_fora_de_sequencia_ainda_recusada(self):
        self._reg(_T.ENTRADA, _m(2026, 8, 24, 8, 0))
        with self.assertRaises(ValidationError):
            validar_sequencia_ponto(self.func, _T.VOLTA_INTERVALO, _m(2026, 8, 24, 12, 0))

    def test_duplicata_recusada(self):
        self._reg(_T.ENTRADA, _m(2026, 8, 24, 8, 0))
        with self.assertRaises(ValidationError):
            validar_sequencia_ponto(self.func, _T.ENTRADA, _m(2026, 8, 24, 8, 0))


class JornadaCalculoTests(TestCase):
    def setUp(self):
        self.func = Usuario.objects.create_user(username="tec2", password="x")
        # jornada padrão: 8h/dia útil
        self.func.periodo1_inicio = None
        self.func.periodo1_fim = None
        self.func.periodo2_inicio = None
        self.func.periodo2_fim = None
        self.func.save()

    def _reg(self, tipo, quando):
        return RegistroPonto.objects.create(
            funcionario=self.func, tipo=tipo, registrado_em=quando
        )

    def test_turno_da_noite_conta_no_dia_que_comecou(self):
        # domingo 30/08 19:00 -> segunda 31/08 00:21  (5h21)
        self._reg(_T.ENTRADA, _m(2026, 8, 30, 19, 0))
        self._reg(_T.SAIDA, _m(2026, 8, 31, 0, 21))

        dias = _calcular_dias(self.func, "2026-08-30", "2026-08-31", None)
        por_data = {str(d["data"]): d for d in dias}

        self.assertEqual(por_data["2026-08-30"]["total_minutos"], 5 * 60 + 21)
        self.assertFalse(por_data["2026-08-30"]["em_aberto"])
        # segunda não herda as horas nem fica "em aberto"
        self.assertEqual(por_data["2026-08-31"]["total_minutos"], 0)
        self.assertFalse(por_data["2026-08-31"]["em_aberto"])

    def test_jornada_aberta_mais_de_24h_e_abandonada(self):
        self._reg(_T.ENTRADA, _m(2026, 8, 24, 8, 0))  # nunca bateu saída
        self._reg(_T.ENTRADA, _m(2026, 8, 26, 8, 0))
        self._reg(_T.SAIDA, _m(2026, 8, 26, 17, 0))

        jornadas = _agrupar_jornadas(list(self.func.registros_ponto.order_by("registrado_em")))
        self.assertEqual(len(jornadas), 2)
        self.assertTrue(jornadas[0]["abandonada"])
        self.assertEqual(_calcular_dias(self.func, "2026-08-24", "2026-08-24", None)[0]["total_minutos"], 0)


class EncarregadoPontoTests(TestCase):
    def setUp(self):
        self.encarregado = Usuario.objects.create_user(
            username="enc", password="x", papel=Usuario.Papel.ENCARREGADO
        )
        self.auxiliar = Usuario.objects.create_user(
            username="aux", password="x", papel=Usuario.Papel.TECNICO,
            encarregado_responsavel=self.encarregado,
        )
        self.api = APIClient()

    def test_encarregado_nao_aprova_solicitacao_de_ponto(self):
        sol = SolicitacaoPonto.objects.create(
            funcionario=self.auxiliar,
            tipo=SolicitacaoPonto.Tipo.JUSTIFICATIVA_AUSENCIA,
            data_referencia="2026-08-20",
            descricao="atestado",
        )
        self.api.force_authenticate(self.encarregado)
        resp = self.api.post(f"/api/solicitacoes-ponto/{sol.id}/aprovar/")
        self.assertEqual(resp.status_code, 403)

    def test_encarregado_so_ve_o_proprio_ponto(self):
        RegistroPonto.objects.create(
            funcionario=self.auxiliar, tipo=RegistroPonto.Tipo.ENTRADA,
            registrado_em=timezone.now(),
        )
        self.api.force_authenticate(self.encarregado)
        resp = self.api.get("/api/registros-ponto/")
        self.assertEqual(resp.data["count"], 0)
