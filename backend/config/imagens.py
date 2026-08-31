"""Compressão das imagens enviadas ao sistema (fotos de etapa de obra hoje;
reaproveitável para as fotos de OS). Fotos de celular chegam com 3–8 MB — o
bucket R2 é pago e a própria API faz o proxy de tudo em /media, então guardar o
arquivo original não compensa."""

import io
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def comprimir_imagem(arquivo, *, max_lado=1600, qualidade=75):
    """Recebe um arquivo de imagem aberto (UploadedFile/FieldFile) e devolve
    ``(nome, ContentFile)`` com um JPEG redimensionado.

    Se o arquivo não for uma imagem que o Pillow entenda, devolve ``(None, None)``
    e cabe ao chamador manter o original."""
    try:
        arquivo.seek(0)
        img = Image.open(arquivo)
        img = ImageOps.exif_transpose(img)  # respeita a orientação da câmera
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((max_lado, max_lado))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=qualidade, optimize=True)
        buffer.seek(0)

        nome_origem = getattr(arquivo, "name", "foto") or "foto"
        nome = Path(nome_origem).stem + ".jpg"
        return nome, ContentFile(buffer.read())
    except Exception:
        return None, None
