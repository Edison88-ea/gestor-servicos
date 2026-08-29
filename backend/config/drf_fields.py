from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.conf import settings
from rest_framework import serializers


class RelativeImageField(serializers.ImageField):
    """Serializa sempre o caminho `/media/<arquivo>` — nunca a URL absoluta do
    storage.

    - A URL absoluta do DRF usa o Host/scheme que chega no Django, que atrás do
      proxy do Vite / de um túnel vira `http://localhost:5173/...` (conteúdo
      misto no celular).
    - Com o storage em R2, `value.url` seria uma URL assinada que expira; o
      caminho `/media/...` é estável, na mesma origem e o service worker do PWA
      já cacheia para uso offline. A view `serve_media` faz o proxy do bucket."""

    def to_representation(self, value):
        if not value:
            return None
        return f"{settings.MEDIA_URL}{value.name}"


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
