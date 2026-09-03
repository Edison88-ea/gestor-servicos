from datetime import datetime, time

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


class ApuracaoPosicionalTests(TestCase):
    """Extra = trabalho fora da janela do horário; falta = janela descoberta.
    O saldo continua sendo trabalhado - carga (= extra - falta)."""

    def setUp(self):
        # horário 09:00-12:00 + 13:30-19:00 = 8h30 (o caso do print do Secullum)
        self.func = Usuario.objects.create_user(username="noturno", password="x")
        self.func.periodo1_inicio = time(9, 0)
        self.func.periodo1_fim = time(12, 0)
        self.func.periodo2_inicio = time(13, 30)
        self.func.periodo2_fim = time(19, 0)
        self.func.save()

    def _reg(self, tipo, quando):
        RegistroPonto.objects.create(funcionario=self.func, tipo=tipo, registrado_em=quando)

    def _dia(self, data_iso):
        return _calcular_dias(self.func, data_iso, data_iso, None)[0]

    def test_turno_noturno_reproduz_secullum(self):
        # Print "Detalhes" do Secullum (31/08): Entrada 22:04, Saída 07:06,
        # Entrada 07:30, Saída 07:40 -> Extras 09:12, Faltas 08:30, Not 06:56,
        # Saldo +00:42
        self._reg(_T.ENTRADA, _m(2026, 8, 31, 22, 4))
        self._reg(_T.SAIDA, _m(2026, 9, 1, 7, 6))
        self._reg(_T.ENTRADA, _m(2026, 9, 1, 7, 30))
        self._reg(_T.SAIDA, _m(2026, 9, 1, 7, 40))

        d = self._dia("2026-08-31")
        self.assertEqual(d["normal_minutos"], 0)
        self.assertEqual(d["extra_minutos"], 9 * 60 + 12)
        self.assertEqual(d["falta_minutos"], 8 * 60 + 30)
        self.assertEqual(d["noturno_minutos"], 6 * 60 + 56)
        self.assertEqual(d["extra_noturno_minutos"], 6 * 60 + 56)
        self.assertEqual(d["saldo_minutos"], 42)
        self.assertEqual(d["saldo_minutos"], d["extra_minutos"] - d["falta_minutos"])

    def test_pausa_curta_apos_meia_noite_fica_no_dia_que_comecou(self):
        # a Entrada 07:30 (24 min depois da Saída 07:06) retoma a mesma jornada
        self._reg(_T.ENTRADA, _m(2026, 8, 31, 22, 4))
        self._reg(_T.SAIDA, _m(2026, 9, 1, 7, 6))
        self._reg(_T.ENTRADA, _m(2026, 9, 1, 7, 30))
        self._reg(_T.SAIDA, _m(2026, 9, 1, 7, 40))

        self.assertEqual(self._dia("2026-09-01")["total_minutos"], 0)
        self.assertEqual(self._dia("2026-08-31")["total_minutos"], 9 * 60 + 12)

    def test_diurno_no_horario_quase_sem_extra_nem_falta(self):
        self._reg(_T.ENTRADA, _m(2026, 9, 2, 9, 3))
        self._reg(_T.SAIDA_INTERVALO, _m(2026, 9, 2, 12, 0))
        self._reg(_T.VOLTA_INTERVALO, _m(2026, 9, 2, 13, 28))
        self._reg(_T.SAIDA, _m(2026, 9, 2, 19, 5))

        d = self._dia("2026-09-02")
        self.assertEqual(d["normal_minutos"], 507)          # 09:03-12:00 + 13:30-19:00
        self.assertEqual(d["extra_minutos"], 7)             # 13:28-13:30 + 19:00-19:05
        self.assertEqual(d["falta_minutos"], 3)             # 09:00-09:03
        self.assertEqual(d["noturno_minutos"], 0)
        self.assertEqual(d["saldo_minutos"], 4)

    def test_fim_de_semana_tudo_extra_sem_falta(self):
        # sábado 05/09: sem janela esperada
        self._reg(_T.ENTRADA, _m(2026, 9, 5, 22, 0))
        self._reg(_T.SAIDA, _m(2026, 9, 6, 6, 0))

        d = self._dia("2026-09-05")
        self.assertTrue(d["folga"])
        self.assertEqual(d["extra_minutos"], 8 * 60)
        self.assertEqual(d["falta_minutos"], 0)
        self.assertEqual(d["noturno_minutos"], 7 * 60)      # 22:00-05:00
        self.assertEqual(d["saldo_minutos"], 8 * 60)

    def test_dia_sem_batida_e_falta_cheia(self):
        d = self._dia("2026-09-02")
        self.assertEqual(d["extra_minutos"], 0)
        self.assertEqual(d["falta_minutos"], 8 * 60 + 30)
        self.assertEqual(d["saldo_minutos"], -(8 * 60 + 30))
