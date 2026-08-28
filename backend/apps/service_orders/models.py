from django.conf import settings
from django.db import models

from apps.clients.models import Cliente


class OrdemServico(models.Model):
    class Status(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"
        ATRIBUIDA = "ATRIBUIDA", "Atribuída"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        PAUSADA = "PAUSADA", "Pausada"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        CANCELADA = "CANCELADA", "Cancelada"

    class Prioridade(models.TextChoices):
        BAIXA = "BAIXA", "Baixa"
        MEDIA = "MEDIA", "Média"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    numero = models.CharField(max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ordens_servico")
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_atribuidas",
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ordens_criadas",
    )
    tipo_servico = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    prioridade = models.CharField(max_length=10, choices=Prioridade.choices, default=Prioridade.MEDIA)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ABERTA)

    checklist = models.JSONField(default=list, blank=True)
    # Relato estruturado preenchido pelo técnico ao concluir:
    # {local, servicos: [str], materiais: [{descricao, quantidade, unidade}],
    #  equipe: [str], observacoes: str}
    relato = models.JSONField(default=dict, blank=True)
    observacoes_tecnico = models.TextField(blank=True)
    assinatura_cliente = models.ImageField(upload_to="assinaturas/%Y/%m/", null=True, blank=True)

    # Preenchidos quando o técnico abre a OS estando fisicamente no local do
    # cliente (fluxo "Estou no local"), para confirmar depois que o
    # atendimento realmente ocorreu onde deveria.
    latitude_abertura = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_abertura = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    data_agendada = models.DateTimeField(null=True, blank=True)
    data_inicio = models.DateTimeField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"OS {self.numero} - {self.cliente.nome}"

    def save(self, *args, **kwargs):
        if not self.numero:
            ultimo = OrdemServico.objects.order_by("-id").first()
            proximo_id = (ultimo.id + 1) if ultimo else 1
            self.numero = f"OS{proximo_id:06d}"
        super().save(*args, **kwargs)


class PausaOrdemServico(models.Model):
    """Registra cada vez que o técnico pausa o atendimento (almoço, falta de
    material, etc.), para dar um histórico e permitir calcular o tempo real
    trabalhado na OS descontando as pausas."""

    class Motivo(models.TextChoices):
        ALMOCO = "ALMOCO", "Almoço"
        FALTA_MATERIAL = "FALTA_MATERIAL", "Falta de material"
        AGUARDANDO_CLIENTE = "AGUARDANDO_CLIENTE", "Aguardando cliente"
        OUTRO = "OUTRO", "Outro"

    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="pausas")
    motivo = models.CharField(max_length=20, choices=Motivo.choices)
    observacao = models.TextField(blank=True)
    iniciada_em = models.DateTimeField(auto_now_add=True)
    retomada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-iniciada_em"]

    def __str__(self):
        return f"Pausa de {self.ordem_servico.numero} ({self.get_motivo_display()})"


class FotoOrdemServico(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name="fotos")
    imagem = models.ImageField(upload_to="ordens_servico/%Y/%m/")
    legenda = models.CharField(max_length=200, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto de {self.ordem_servico.numero}"


class ServicoCatalogo(models.Model):
    """Descrições de serviço já usadas em OS concluídas, para sugerir no
    formulário de relato. Preenchido automaticamente ao concluir uma OS."""

    descricao = models.CharField(max_length=300, unique=True)
    usos = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-usos", "descricao"]
        verbose_name = "serviço do catálogo"
        verbose_name_plural = "catálogo de serviços"

    def __str__(self):
        return self.descricao


class MaterialCatalogo(models.Model):
    """Materiais já usados em OS concluídas, para sugerir no formulário de
    relato (com a unidade). Preenchido automaticamente ao concluir uma OS."""

    descricao = models.CharField(max_length=200, unique=True)
    unidade_padrao = models.CharField(max_length=10, blank=True)
    usos = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-usos", "descricao"]
        verbose_name = "material do catálogo"
        verbose_name_plural = "catálogo de materiais"

    def __str__(self):
        return self.descricao
