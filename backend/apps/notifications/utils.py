from .models import Notificacao


def notificar(destinatario, tipo, mensagem, link=""):
    """Cria uma notificação. destinatario=None é ignorado silenciosamente
    (ex.: OS criada sem técnico definido ainda)."""
    if destinatario is None:
        return None
    return Notificacao.objects.create(
        destinatario=destinatario, tipo=tipo, mensagem=mensagem, link=link
    )


def notificar_muitos(destinatarios, tipo, mensagem, link=""):
    """Cria a mesma notificação para vários destinatários num único INSERT
    (evita uma query por pessoa quando se avisa 'toda a gestão')."""
    objs = [
        Notificacao(destinatario=d, tipo=tipo, mensagem=mensagem, link=link)
        for d in destinatarios
        if d is not None
    ]
    return Notificacao.objects.bulk_create(objs)
