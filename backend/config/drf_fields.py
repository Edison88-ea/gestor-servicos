from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from rest_framework import serializers


class RoundedDecimalField(serializers.DecimalField):
    """DecimalField que arredonda a entrada antes de validar.

    O GPS do celular manda números com muitas casas decimais; sem isto o DRF
    rejeita com "não haja mais de N dígitos no total" e a batida de ponto /
    abertura de OS falha (ou some da fila offline)."""

    def to_internal_value(self, data):
        if data not in (None, ""):
            try:
                quantum = Decimal(1).scaleb(-self.decimal_places)  # ex.: 0.000001
                data = Decimal(str(data)).quantize(quantum, rounding=ROUND_HALF_UP)
            except (InvalidOperation, TypeError, ValueError):
                pass
        return super().to_internal_value(data)


class CoordinateField(RoundedDecimalField):
    """Latitude / longitude (6 casas ≈ 11 cm)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 9)
        kwargs.setdefault("decimal_places", 6)
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)


class MetersField(RoundedDecimalField):
    """Precisão do GPS em metros."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", 8)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)
