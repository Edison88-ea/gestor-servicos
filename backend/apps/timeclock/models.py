from django.conf import settings
from django.db import models


class RegistroPonto(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SAIDA_INTERVALO = "SAIDA_INTERVALO", "Saída para intervalo"
        VOLTA_INTERVALO = "VOLTA_INTERVALO", "Volta do intervalo"
        SAIDA = "SAIDA", "Saída"

    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registros_ponto"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)

    # Momento em que o funcionário efetivamente bateu o ponto (enviado pelo
    # cliente/PWA). Pode ser diferente de `sincronizado_em` quando o registro
    # foi feito offline e sincronizado depois.
    registrado_em = models.DateTimeField()
    sincronizado_em = models.DateTimeField(auto_now_add=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    precisao_metros = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Precisão (raio, em metros) informada pelo GPS do dispositivo no momento do registro.",
    )
    endereco = models.CharField(max_length=255, blank=True, help_text="Endereço aproximado (geocodificação reversa).")
    justificativa = models.TextField(blank=True)
    foto = models.ImageField(upload_to="ponto/%Y/%m/", null=True, blank=True)

    origem_offline = models.BooleanField(
        default=False, help_text="Marcado quando o registro foi feito sem conexão e sincronizado depois."
    )

    class Meta:
        ordering = ["-registrado_em"]

    def __str__(self):
        return f"{self.funcionario} - {self.get_tipo_display()} em {self.registrado_em:%d/%m/%Y %H:%M}"


class SolicitacaoPonto(models.Model):
    """Pedido do funcionário para ajustar um ponto que faltou bater, ou para
    justificar uma ausência num dia. Sempre passa por aprovação de
    gestor/RH - nunca cria ou altera o RegistroPonto diretamente."""

    class Tipo(models.TextChoices):
        AJUSTE = "AJUSTE", "Ajuste de ponto"
        AJUSTE_DIA = "AJUSTE_DIA", "Ajuste do dia inteiro"
        JUSTIFICATIVA_AUSENCIA = "JUSTIFICATIVA_AUSENCIA", "Justificativa de ausência"

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        APROVADA = "APROVADA", "Aprovada"
        REJEITADA = "REJEITADA", "Rejeitada"

    funcionario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitacoes_ponto"
    )
    tipo = models.CharField(max_length=25, choices=Tipo.choices)
    data_referencia = models.DateField(help_text="Dia a que a solicitação se refere.")

    # Só usados quando tipo=AJUSTE
    tipo_ponto_solicitado = models.CharField(max_length=20, choices=RegistroPonto.Tipo.choices, blank=True)
    horario_solicitado = models.TimeField(null=True, blank=True)

    # Só usados quando tipo=AJUSTE_DIA. Lista de {tipo, horario} que o
    # funcionário propõe como o conjunto correto de batidas do dia.
    # `pontos_anteriores` é a fotografia do que havia quando ele pediu.
    pontos_propostos = models.JSONField(default=list, blank=True)
    pontos_anteriores = models.JSONField(default=list, blank=True)

    descricao = models.TextField(help_text="Motivo/justificativa do funcionário.")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)

    analisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_analisadas",
    )
    analisado_em = models.DateTimeField(null=True, blank=True)
    resposta_gestor = models.TextField(blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.funcionario} - {self.get_tipo_display()} ({self.data_referencia})"
