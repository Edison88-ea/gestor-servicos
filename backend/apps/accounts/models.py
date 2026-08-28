from datetime import time

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Papel(models.TextChoices):
        TECNICO = "TECNICO", "Técnico"
        GESTOR = "GESTOR", "Gestor"
        RH = "RH", "RH"
        ADMIN = "ADMIN", "Administrador"

    papel = models.CharField(
        max_length=20, choices=Papel.choices, default=Papel.TECNICO
    )
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    ativo_desde = models.DateField(null=True, blank=True)

    # Jornada de trabalho (definida pelo RH, não pelo próprio funcionário):
    # até dois períodos por dia útil (segunda a sexta), ex. manhã e tarde.
    # Deixar um período em branco significa que ele não existe para essa jornada.
    periodo1_inicio = models.TimeField(null=True, blank=True, default=time(8, 0))
    periodo1_fim = models.TimeField(null=True, blank=True, default=time(12, 0))
    periodo2_inicio = models.TimeField(null=True, blank=True, default=time(13, 0))
    periodo2_fim = models.TimeField(null=True, blank=True, default=time(18, 0))

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def carga_horaria_diaria_minutos(self):
        """Minutos esperados por dia útil, somando os períodos configurados."""
        total = 0
        for inicio, fim in ((self.periodo1_inicio, self.periodo1_fim), (self.periodo2_inicio, self.periodo2_fim)):
            if inicio and fim:
                total += (fim.hour * 60 + fim.minute) - (inicio.hour * 60 + inicio.minute)
        return max(total, 0)
