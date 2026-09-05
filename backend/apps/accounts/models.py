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

    class EstadoCivil(models.TextChoices):
        SOLTEIRO = "SOLTEIRO", "Solteiro(a)"
        CASADO = "CASADO", "Casado(a)"
        DIVORCIADO = "DIVORCIADO", "Divorciado(a)"
        VIUVO = "VIUVO", "Viúvo(a)"
        UNIAO_ESTAVEL = "UNIAO_ESTAVEL", "União estável"

    class Genero(models.TextChoices):
        MASCULINO = "MASCULINO", "Masculino"
        FEMININO = "FEMININO", "Feminino"
        OUTRO = "OUTRO", "Outro"
        NAO_INFORMAR = "NAO_INFORMAR", "Prefiro não informar"

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

    # Nem todo mundo bate ponto, e isso não decorre do papel: a secretária é RH
    # (cuida do ponto e das OS de todos) e ainda registra o próprio ponto; a
    # dona da empresa acompanha a gestão e não bate ponto. Por isso um campo,
    # e não uma regra em cima de `papel`.
    registra_ponto = models.BooleanField(
        "registra ponto",
        default=True,
        help_text="Desmarque para quem não bate ponto (sócios, diretoria).",
    )

    # Jornada de trabalho (definida pelo RH, não pelo próprio funcionário):
    # até dois períodos por dia útil (segunda a sexta), ex. manhã e tarde.
    # Deixar um período em branco significa que ele não existe para essa jornada.
    periodo1_inicio = models.TimeField(null=True, blank=True, default=time(8, 0))
    periodo1_fim = models.TimeField(null=True, blank=True, default=time(12, 0))
    periodo2_inicio = models.TimeField(null=True, blank=True, default=time(13, 0))
    periodo2_fim = models.TimeField(null=True, blank=True, default=time(18, 0))

    # --- Dados cadastrais (mantidos pelo RH; ver apps.accounts.FuncionarioViewSet) ---
    # Pessoais
    data_nascimento = models.DateField(null=True, blank=True)
    estado_civil = models.CharField(max_length=20, blank=True, choices=EstadoCivil.choices)
    genero = models.CharField(max_length=20, blank=True, choices=Genero.choices)
    nome_mae = models.CharField(max_length=150, blank=True)
    # Documentos
    cpf = models.CharField(max_length=14, blank=True)
    rg = models.CharField(max_length=20, blank=True)
    pis = models.CharField("PIS/NIS", max_length=20, blank=True)
    ctps_numero = models.CharField("CTPS nº", max_length=20, blank=True)
    ctps_serie = models.CharField("CTPS série", max_length=20, blank=True)
    # Endereço
    cep = models.CharField(max_length=9, blank=True)
    logradouro = models.CharField(max_length=150, blank=True)
    numero_endereco = models.CharField("número", max_length=10, blank=True)
    complemento = models.CharField(max_length=60, blank=True)
    bairro = models.CharField(max_length=80, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    estado = models.CharField("UF", max_length=2, blank=True)
    # Contrato
    data_admissao = models.DateField(null=True, blank=True)
    data_desligamento = models.DateField(null=True, blank=True)
    salario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Bancários
    banco = models.CharField(max_length=60, blank=True)
    agencia = models.CharField(max_length=15, blank=True)
    conta = models.CharField(max_length=20, blank=True)
    pix = models.CharField(max_length=140, blank=True)
    # Contato de emergência
    contato_emergencia_nome = models.CharField(max_length=120, blank=True)
    contato_emergencia_telefone = models.CharField(max_length=20, blank=True)
    contato_emergencia_parentesco = models.CharField(max_length=40, blank=True)

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
