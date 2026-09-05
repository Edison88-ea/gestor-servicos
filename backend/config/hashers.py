"""Hasher de senha do projeto.

Argon2id com os parâmetros mínimos recomendados pelo OWASP (m=19 MiB, t=2,
p=1) em vez do padrão do Django (~100 MiB por hash) — o serviço roda no plano
free do Render (512 MB, 1 worker) e não vale gastar 100 MiB por login.
"""

from django.contrib.auth.hashers import Argon2PasswordHasher


class Argon2Hasher(Argon2PasswordHasher):
    time_cost = 2
    memory_cost = 19456  # KiB (~19 MiB) — mínimo OWASP para Argon2id
    parallelism = 1
