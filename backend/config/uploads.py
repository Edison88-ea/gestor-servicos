"""Limites de upload — defesa contra arquivos grandes / bombas de descompressão.

Três barreiras, da mais externa para a mais interna:

1. ``LimiteTamanhoRequisicaoMiddleware`` — rejeita pelo ``Content-Length`` antes
   de o Django materializar o upload em disco.
2. ``RelativeImageField`` / ``RelativeFileField`` (config.drf_fields) — checam o
   tamanho do arquivo antes de o serializer abrir a imagem no Pillow.
3. ``config.imagens`` — ``Image.MAX_IMAGE_PIXELS`` limita a área da imagem
   decodificada (bomba de descompressão de imagem).
"""

from django.http import JsonResponse

# Limite por campo, em MB.
MAX_MB_IMAGEM = 15
MAX_MB_ARQUIVO = 25

# Teto do corpo da requisição: folga sobre o maior limite de campo, para o
# multipart (boundaries, outros campos) caber.
MAX_BYTES_REQUISICAO = 30 * 1024 * 1024

_METODOS_COM_CORPO = ("POST", "PUT", "PATCH")


class LimiteTamanhoRequisicaoMiddleware:
    """Corta cedo requisições com corpo grande demais, pelo cabeçalho
    ``Content-Length`` — antes de o upload ser gravado no disco efêmero do
    servidor. O limite por campo é a segunda barreira, para o cliente que
    mente no cabeçalho ou usa transfer-encoding chunked."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in _METODOS_COM_CORPO:
            tamanho = request.META.get("CONTENT_LENGTH")
            if tamanho:
                try:
                    grande_demais = int(tamanho) > MAX_BYTES_REQUISICAO
                except (TypeError, ValueError):
                    grande_demais = False
                if grande_demais:
                    return JsonResponse(
                        {"detail": "Arquivo grande demais para enviar."},
                        status=413,
                    )
        return self.get_response(request)
