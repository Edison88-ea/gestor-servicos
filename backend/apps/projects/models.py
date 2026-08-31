from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Sum

from config.imagens import comprimir_imagem


class Projeto(models.Model):
    """Um "Termo de Mudança de Layout": o escopo de instalação de pontos
    (rede, ar, energia, etc.) para um setor/linha da fábrica."""

    class Status(models.TextChoices):
        PLANEJADO = "PLANEJADO", "Planejado"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        CONCLUIDO = "CONCLUIDO", "Concluído"
        CANCELADO = "CANCELADO", "Cancelado"

    class Tipo(models.TextChoices):
        INSTALACAO_PROJETO = "INSTALACAO_PROJETO", "Instalação de projeto"
        MUDANCA_LAYOUT = "MUDANCA_LAYOUT", "Mudança de layout"
        MANUTENCAO = "MANUTENCAO", "Manutenção"
        OUTRO = "OUTRO", "Outro"

    numero = models.CharField(max_length=20, unique=True, editable=False)
    nome = models.CharField(max_length=200)
    descricao = models.TextField("Escopo", blank=True)
    responsavel = models.CharField(max_length=150, blank=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.INSTALACAO_PROJETO)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PLANEJADO)
    areas_afetadas = models.JSONField(default=list, blank=True)

    data_mudanca = models.DateField(null=True, blank=True)
    data_termino_previsto = models.DateField(null=True, blank=True)
    data_conclusao = models.DateField(null=True, blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="projetos_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "projeto (obra)"
        verbose_name_plural = "projetos (obras)"

    def __str__(self):
        return f"{self.numero} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.numero:
            ultimo = Projeto.objects.order_by("-id").first()
            proximo = (ultimo.id + 1) if ultimo else 1
            self.numero = f"PRJ{proximo:06d}"
        super().save(*args, **kwargs)

    def _totais(self):
        return self.etapas.aggregate(meta=Sum("meta"), realizado=Sum("realizado"))

    @property
    def total_meta(self):
        return self._totais()["meta"] or 0

    @property
    def total_realizado(self):
        return self._totais()["realizado"] or 0

    @property
    def progresso(self):
        """Percentual concluído: soma dos realizados / soma das metas (teto 100)."""
        totais = self._totais()
        meta = totais["meta"] or 0
        if meta == 0:
            return 0
        realizado = totais["realizado"] or 0
        return int(min(realizado / meta * 100, 100))


class Etapa(models.Model):
    """Um item do escopo: quantos pontos de um tipo instalar num trecho."""

    class TipoPonto(models.TextChoices):
        REDE = "REDE", "Ponto de rede"
        AR = "AR", "Ponto de ar"
        ENERGIA = "ENERGIA", "Ponto de energia"
        TELEFONE = "TELEFONE", "Ponto de telefone"
        LPRS = "LPRS", "Ponto de LPRS"
        REDE_ESTABILIZADA = "REDE_ESTABILIZADA", "Rede estabilizada elétrica"
        ELETRICA_220 = "ELETRICA_220", "Elétrica 220V"
        OUTRO = "OUTRO", "Outro"

    projeto = models.ForeignKey(Projeto, related_name="etapas", on_delete=models.CASCADE)
    nome = models.CharField(max_length=200)
    tipo_ponto = models.CharField(max_length=20, choices=TipoPonto.choices, blank=True)
    localizacao = models.CharField(max_length=200, blank=True)
    meta = models.PositiveIntegerField("Quantidade prevista", default=1)
    realizado = models.PositiveIntegerField("Quantidade instalada", default=0)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.nome} ({self.realizado}/{self.meta})"

    @property
    def concluida(self):
        return bool(self.meta) and self.realizado >= self.meta

    @property
    def porcentagem(self):
        if not self.meta:
            return 0
        return int(min(self.realizado / self.meta * 100, 100))


class FotoEtapa(models.Model):
    etapa = models.ForeignKey(Etapa, related_name="fotos", on_delete=models.CASCADE)
    imagem = models.ImageField(upload_to="obras/etapas/%Y/%m/")
    legenda = models.CharField(max_length=200, blank=True)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enviado_em"]

    def __str__(self):
        return f"Foto de {self.etapa}"

    def save(self, *args, **kwargs):
        # Comprime só no envio (registro novo); fotos não são reeditadas depois.
        if self.imagem and not self.pk:
            nome, comprimida = comprimir_imagem(self.imagem)
            if comprimida is not None:
                self.imagem.save(nome, comprimida, save=False)
        super().save(*args, **kwargs)


class PlantaProjeto(models.Model):
    """Folha da planta anexada ao Termo (PDF ou imagem)."""

    projeto = models.ForeignKey(Projeto, related_name="plantas", on_delete=models.CASCADE)
    arquivo = models.FileField(
        upload_to="obras/plantas/%Y/%m/",
        validators=[FileExtensionValidator(["pdf", "png", "jpg", "jpeg", "webp"])],
    )
    pagina = models.PositiveIntegerField(null=True, blank=True)
    descricao = models.CharField(max_length=200, blank=True)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pagina", "id"]

    def __str__(self):
        return f"Planta de {self.projeto.numero} (folha {self.pagina or '?'})"


class HistoricoEtapa(models.Model):
    etapa = models.ForeignKey(Etapa, related_name="historico", on_delete=models.CASCADE)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    data = models.DateTimeField(auto_now_add=True)
    quantidade_anterior = models.PositiveIntegerField()
    quantidade_nova = models.PositiveIntegerField()
    observacao = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        quem = self.usuario.get_username() if self.usuario else "Sistema"
        return f"{quem}: {self.quantidade_anterior} -> {self.quantidade_nova}"


class AssinaturaProjeto(models.Model):
    class Papel(models.TextChoices):
        CIENTE = "CIENTE", "Ciente da alteração"
        SUPERVISOR = "SUPERVISOR", "Supervisor de processos"

    projeto = models.ForeignKey(Projeto, related_name="assinaturas", on_delete=models.CASCADE)
    papel = models.CharField(max_length=15, choices=Papel.choices)
    nome = models.CharField(max_length=150)
    assinatura = models.ImageField(upload_to="obras/assinaturas/%Y/%m/")
    assinado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["assinado_em"]

    def __str__(self):
        return f"{self.get_papel_display()} - {self.nome}"
