from .models import Notificacao


def notificar(destinatario, tipo, mensagem, link=""):
    """Cria uma notificação. destinatario=None é ignorado silenciosamente
    (ex.: OS criada sem técnico definido ainda)."""
    if destinatario is None:
        return None
    return Notificacao.objects.create(
        destinatario=destinatario, tipo=tipo, mensagem=mensagem, link=link
    )
