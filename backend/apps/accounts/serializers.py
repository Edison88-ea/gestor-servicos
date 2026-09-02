from rest_framework import serializers

from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """Versão enxuta: usada no /usuarios/ (escolher técnico numa OS) e no
    /usuarios/me/ (perfil do logado). Não expõe dados cadastrais sensíveis."""

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "papel",
            "encarregado_responsavel",
            "telefone",
            "cargo",
            "periodo1_inicio",
            "periodo1_fim",
            "periodo2_inicio",
            "periodo2_fim",
            "carga_horaria_diaria_minutos",
            "is_active",
        )
        read_only_fields = ("carga_horaria_diaria_minutos",)


class FuncionarioSerializer(serializers.ModelSerializer):
    """Cadastro completo do funcionário — mantido pelo RH em /funcionarios/."""

    nome_completo = serializers.SerializerMethodField()
    papel_display = serializers.CharField(source="get_papel_display", read_only=True)
    estado_civil_display = serializers.CharField(source="get_estado_civil_display", read_only=True)
    genero_display = serializers.CharField(source="get_genero_display", read_only=True)
    encarregado_responsavel_nome = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=6)

    class Meta:
        model = Usuario
        fields = (
            "id",
            # acesso
            "username",
            "password",
            "papel",
            "papel_display",
            "is_active",
            # identificação
            "first_name",
            "last_name",
            "nome_completo",
            "email",
            "telefone",
            # pessoais
            "data_nascimento",
            "estado_civil",
            "estado_civil_display",
            "genero",
            "genero_display",
            "nome_mae",
            # documentos
            "cpf",
            "rg",
            "pis",
            "ctps_numero",
            "ctps_serie",
            # endereço
            "cep",
            "logradouro",
            "numero_endereco",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            # profissional
            "cargo",
            "encarregado_responsavel",
            "encarregado_responsavel_nome",
            "ativo_desde",
            "data_admissao",
            "data_desligamento",
            "salario",
            # jornada
            "periodo1_inicio",
            "periodo1_fim",
            "periodo2_inicio",
            "periodo2_fim",
            "carga_horaria_diaria_minutos",
            # bancários
            "banco",
            "agencia",
            "conta",
            "pix",
            # emergência
            "contato_emergencia_nome",
            "contato_emergencia_telefone",
            "contato_emergencia_parentesco",
        )
        read_only_fields = (
            "carga_horaria_diaria_minutos",
            "papel_display",
            "estado_civil_display",
            "genero_display",
            "nome_completo",
            "encarregado_responsavel_nome",
        )

    def get_nome_completo(self, obj):
        return obj.get_full_name() or obj.username

    def get_encarregado_responsavel_nome(self, obj):
        enc = obj.encarregado_responsavel
        return (enc.get_full_name() or enc.username) if enc else None

    def validate_username(self, value):
        qs = Usuario.objects.filter(username__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Já existe um funcionário com esse usuário.")
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Defina uma senha inicial para o novo funcionário."})
        return attrs

    def create(self, validated_data):
        senha = validated_data.pop("password", None)
        usuario = Usuario(**validated_data)
        usuario.set_password(senha)
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        senha = validated_data.pop("password", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if senha:
            instance.set_password(senha)
        instance.save()
        return instance
