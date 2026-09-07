from decimal import Decimal, InvalidOperation

from django.db.models import F
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.service_orders.models import MaterialCatalogo

from .models import Material, MovimentoEstoque
from .movimentos import aplicar_ajuste, aplicar_entrada
from .permissions import PodeGerenciarEstoque
from .serializers import MaterialSerializer, MovimentoEstoqueSerializer

_VERDADEIRO = {"1", "true", "True", "sim"}
_FALSO = {"0", "false", "False", "nao", "não"}


def _decimal(valor, campo):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError):
        raise ValidationError({campo: "Informe um número."})


class MaterialViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialSerializer
    permission_classes = [PodeGerenciarEstoque]
    filter_backends = [filters.SearchFilter]
    search_fields = ["descricao"]

    def get_queryset(self):
        qs = Material.objects.all()
        p = self.request.query_params
        if p.get("ativo") in _VERDADEIRO:
            qs = qs.filter(ativo=True)
        elif p.get("ativo") in _FALSO:
            qs = qs.filter(ativo=False)
        if p.get("abaixo_minimo") in _VERDADEIRO:
            qs = qs.filter(estoque_minimo__gt=0, saldo__lt=F("estoque_minimo"))
        return qs

    def perform_create(self, serializer):
        material = serializer.save()
        saldo_inicial = self.request.data.get("saldo_inicial")
        if saldo_inicial in (None, "", "0"):
            return
        qtd = _decimal(saldo_inicial, "saldo_inicial")
        if qtd <= 0:
            return
        custo = self.request.data.get("custo_inicial")
        custo = _decimal(custo, "custo_inicial") if custo not in (None, "") else None
        aplicar_entrada(
            material,
            qtd,
            custo_unitario=custo,
            observacao="Cadastro inicial",
            usuario=self.request.user,
        )

    @action(detail=False, methods=["get"])
    def resumo(self, request):
        qs = Material.objects.filter(ativo=True)
        valor = sum((m.valor_em_estoque for m in qs), Decimal("0"))
        return Response(
            {
                "total_itens": qs.count(),
                "valor_em_estoque": str(valor),
                "abaixo_minimo": sum(1 for m in qs if m.abaixo_minimo),
            }
        )

    @action(detail=True, methods=["get"])
    def movimentos(self, request, pk=None):
        material = self.get_object()
        qs = material.movimentos.select_related("usuario", "ordem_servico")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                MovimentoEstoqueSerializer(page, many=True).data
            )
        return Response(MovimentoEstoqueSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def entrada(self, request, pk=None):
        material = self.get_object()
        qtd = _decimal(request.data.get("quantidade"), "quantidade")
        if qtd <= 0:
            raise ValidationError({"quantidade": "A entrada precisa ser maior que zero."})
        custo = request.data.get("custo_unitario")
        custo = _decimal(custo, "custo_unitario") if custo not in (None, "") else None
        if custo is not None and custo < 0:
            raise ValidationError({"custo_unitario": "O custo não pode ser negativo."})
        mov = aplicar_entrada(
            material,
            qtd,
            custo_unitario=custo,
            documento=request.data.get("documento", ""),
            observacao=request.data.get("observacao", ""),
            usuario=request.user,
        )
        return Response(MovimentoEstoqueSerializer(mov).data, status=201)

    @action(detail=True, methods=["post"])
    def ajuste(self, request, pk=None):
        material = self.get_object()
        saldo = _decimal(request.data.get("saldo_contado"), "saldo_contado")
        if saldo < 0:
            raise ValidationError({"saldo_contado": "O saldo contado não pode ser negativo."})
        mov = aplicar_ajuste(
            material,
            saldo,
            observacao=request.data.get("observacao", ""),
            usuario=request.user,
        )
        return Response(MovimentoEstoqueSerializer(mov).data, status=201)

    @action(detail=False, methods=["get", "post"], url_path="do-catalogo")
    def do_catalogo(self, request):
        """GET: materiais do catálogo de OS que ainda não são item de estoque.
        POST ``{descricoes: [...]}``: cria item de estoque (saldo 0) para cada
        um."""
        ja_sao_item = {
            d.lower() for d in Material.objects.values_list("descricao", flat=True)
        }
        pendentes = [
            {"descricao": c.descricao, "unidade": c.unidade_padrao, "usos": c.usos}
            for c in MaterialCatalogo.objects.all()
            if c.descricao.lower() not in ja_sao_item
        ]
        if request.method == "GET":
            return Response(pendentes)

        por_desc = {p["descricao"].lower(): p for p in pendentes}
        criados = []
        for desc in request.data.get("descricoes") or []:
            info = por_desc.get(str(desc).strip().lower())
            if not info:
                continue
            if Material.objects.filter(descricao__iexact=info["descricao"]).exists():
                continue
            material = Material.objects.create(
                descricao=info["descricao"], unidade=info["unidade"] or ""
            )
            criados.append(MaterialSerializer(material).data)
        return Response({"criados": criados}, status=201)


class MovimentoEstoqueViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovimentoEstoqueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = MovimentoEstoque.objects.select_related(
            "material", "usuario", "ordem_servico"
        )
        p = self.request.query_params
        if p.get("material"):
            qs = qs.filter(material_id=p["material"])
        if p.get("ordem_servico"):
            qs = qs.filter(ordem_servico_id=p["ordem_servico"])
        if p.get("tipo"):
            qs = qs.filter(tipo=p["tipo"].upper())
        if p.get("desde"):
            qs = qs.filter(criado_em__date__gte=p["desde"])
        return qs
