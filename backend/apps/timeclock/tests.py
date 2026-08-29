from datetime import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Usuario

from .models import RegistroPonto
from .views import validar_sequencia_ponto

_T = RegistroPonto.Tipo


def _momento(h, m):
    return timezone.make_aware(datetime(2026, 8, 29, h, m))


class ValidarSequenciaPontoTests(TestCase):
    def setUp(self):
        self.func = Usuario.objects.create_user(username="tec", password="x")

    def _registrar(self, tipo, h, m):
        RegistroPonto.objects.create(
            funcionario=self.func, tipo=tipo, registrado_em=_momento(h, m)
        )

    def test_saida_intervalo_atrasada_valida_mesmo_apos_saida_ja_salva(self):
        """Cenário do bug: a Saída (offline) sincronizou primeiro; a Saída para
        intervalo, feita antes no relógio, chega depois. Deve ser aceita."""
        self._registrar(_T.ENTRADA, 8, 0)
        self._registrar(_T.SAIDA, 17, 0)

        # não deve levantar
        validar_sequencia_ponto(self.func, _T.SAIDA_INTERVALO, _momento(12, 0))

    def test_batida_fora_de_sequencia_ainda_e_recusada(self):
        self._registrar(_T.ENTRADA, 8, 0)
        with self.assertRaises(ValidationError):
            # volta do intervalo sem ter saído para o intervalo
            validar_sequencia_ponto(self.func, _T.VOLTA_INTERVALO, _momento(12, 0))

    def test_duplicata_recusada(self):
        self._registrar(_T.ENTRADA, 8, 0)
        with self.assertRaises(ValidationError):
            validar_sequencia_ponto(self.func, _T.ENTRADA, _momento(8, 0))

    def test_entrada_antes_de_tudo_quando_falta_entrada(self):
        self._registrar(_T.SAIDA_INTERVALO, 12, 0)  # dia bagunçado
        with self.assertRaises(ValidationError):
            # inserir algo antes sem Entrada no início
            validar_sequencia_ponto(self.func, _T.SAIDA, _momento(9, 0))
