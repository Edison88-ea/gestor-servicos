from django.conf import settings
from django.db import models


class Notificacao(models.Model):
    class Tipo(models.TextChoices):
        OS_ATRIBUIDA = "OS_ATRIBUIDA", "Ordem de serviço atribuída"
        SOLICITACAO_APROVADA = "SOLICITACAO_APROVADA", "Solicitação aprovada"
        SOLICITACAO_REJEITADA = "SOLICITACAO_REJEITADA", "Solicitação rejeitada"
        NOVA_SOLICITACAO = "NOVA_SOLICITACAO", "Nova solicitação para revisar"

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    mensagem = models.CharField(max_length=255)
    link = models.CharField(max_length=200, blank=True, help_text="Rota do app pra abrir ao tocar na notificação.")
    lida = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.destinatario}: {self.mensagem}"
