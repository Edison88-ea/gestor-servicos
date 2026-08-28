"""Cria/atualiza um superusuário a partir de variáveis de ambiente.

Necessário porque o plano free do Render não dá acesso a shell para rodar
`createsuperuser` interativamente. É idempotente: rodar de novo num deploy
seguinte não quebra e não recria o usuário.

Variáveis usadas:
  DJANGO_SUPERUSER_USERNAME   (obrigatória)
  DJANGO_SUPERUSER_PASSWORD   (obrigatória)
  DJANGO_SUPERUSER_EMAIL      (opcional)
  DJANGO_SUPERUSER_RESET_PASSWORD=1  -> redefine a senha de um usuário já existente
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Cria ou atualiza um superusuário a partir das variáveis DJANGO_SUPERUSER_*."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

        if not username or not password:
            self.stdout.write(
                "DJANGO_SUPERUSER_USERNAME/PASSWORD não definidos; nada a fazer."
            )
            return

        user, created = User.objects.get_or_create(
            username=username, defaults={"email": email}
        )

        user.is_staff = True
        user.is_superuser = True
        if email:
            user.email = email
        if hasattr(User, "Papel"):
            user.papel = User.Papel.ADMIN
        if created or os.environ.get("DJANGO_SUPERUSER_RESET_PASSWORD") == "1":
            user.set_password(password)
        user.save()

        acao = "criado" if created else "atualizado"
        self.stdout.write(self.style.SUCCESS(f"Superusuário '{username}' {acao}."))
