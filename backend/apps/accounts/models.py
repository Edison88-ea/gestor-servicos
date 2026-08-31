from datetime import time

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Papel(models.TextChoices):
        TECNICO = "TECNICO", "Técnico"
        ENCARREGADO = "ENCARREGADO", "Encarregado"
        GESTOR = "GESTOR", "Gestor"
        RH = "RH", "RH"
        ADMIN = "ADMIN", "Administrador"

    papel = models.CharField(
        max_length=20, choices=Papel.choices, default=Papel.TECNICO
    )
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    ativo_desde = models.DateField(null=True, blank=True)

    # Encarregado a quem este funcionário se reporta. Serve para o encarregado
    # enxergar as OS da equipe dele na própria lista (ver service_orders).
    encarregado_responsavel = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipe",
        limit_choices_to={"papel": Papel.ENCARREGADO},
    )

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
    def e_gestao(self):
        """Gestor, RH ou Admin: vê dados de todos e aprova solicitações.
        Técnico e Encarregado são funcionários de campo (veem os próprios
        dados de ponto; o encarregado só tem a mais a visão das OS da equipe)."""
        return self.papel in (self.Papel.GESTOR, self.Papel.RH, self.Papel.ADMIN)

    @property
    def carga_horaria_diaria_minutos(self):
        """Minutos esperados por dia útil, somando os períodos configurados."""
        total = 0
        for inicio, fim in ((self.periodo1_inicio, self.periodo1_fim), (self.periodo2_inicio, self.periodo2_fim)):
            if inicio and fim:
                total += (fim.hour * 60 + fim.minute) - (inicio.hour * 60 + inicio.minute)
        return max(total, 0)
