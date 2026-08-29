"""
Django settings for config project.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

# Origens confiáveis para CSRF (admin / browsable API). Em produção normalmente
# igual ao ALLOWED_HOSTS com esquema; em teste via túnel (ngrok/cloudflared)
# aceita o curinga do subdomínio, ex.: https://*.ngrok-free.app
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# O Render injeta o hostname público do serviço automaticamente; assim não é
# preciso editar ALLOWED_HOSTS a cada deploy nem saber a URL de antemão.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Atrás do proxy do Render (HTTPS termina no load balancer deles), é o cabeçalho
# X-Forwarded-Proto que diz se a conexão original do usuário era segura.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# IA para padronizar o relato das OS (opcional). Sem provedor configurado, o
# endpoint /padronizar-relato/ responde 503 e o app segue funcionando normal.
#   RELATO_IA_PROVEDOR = "anthropic"  -> usa ANTHROPIC_API_KEY (cobrança Anthropic)
#   RELATO_IA_PROVEDOR = "bedrock"    -> usa AWS (cobrança na fatura da AWS)
RELATO_IA_PROVEDOR = env("RELATO_IA_PROVEDOR", default="anthropic")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
AWS_BEDROCK_REGION = env("AWS_BEDROCK_REGION", default="us-east-1")
# Vazio = usa o padrão do provedor. No Bedrock costuma ser um inference profile
# tipo "us.anthropic.claude-haiku-4-5" (veja no console do Bedrock).
RELATO_IA_MODELO = env("RELATO_IA_MODELO", default="")

# Reforços de segurança que só fazem sentido com DEBUG=False e HTTPS já
# funcionando no domínio de produção. HSTS não é ativado automaticamente
# aqui de propósito: ativar antes de confirmar que o HTTPS está 100% OK
# pode deixar usuários bloqueados até o cabeçalho expirar no navegador.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # local apps
    "apps.accounts",
    "apps.clients",
    "apps.service_orders",
    "apps.timeclock",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.logging_middleware.APILoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# Defaults to SQLite for local development; set DATABASE_URL in .env to use
# PostgreSQL on the company server, e.g.:
# DATABASE_URL=postgres://user:password@localhost:5432/gestor_servicos

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}


# Custom user model (funcionários: técnicos, gestores, RH, admin)
AUTH_USER_MODEL = "accounts.Usuario"


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Static & media files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

# Armazenamento das fotos/assinaturas em bucket S3-compatível (Cloudflare R2).
# Sem R2_BUCKET definido, cai no disco local (dev) — que no plano free do Render
# é efêmero e some a cada deploy. Ver DEPLOY.md.
#
# O bucket é privado: as imagens continuam sendo servidas pela própria API em
# /media/... (a view faz o proxy do storage). Assim as URLs seguem estáveis e
# na mesma origem — sem URL assinada expirando, sem CORS, sem bucket público.
R2_BUCKET = env("R2_BUCKET", default="")
if R2_BUCKET:
    AWS_STORAGE_BUCKET_NAME = R2_BUCKET
    AWS_S3_ENDPOINT_URL = env("R2_ENDPOINT")  # https://<accountid>.r2.cloudflarestorage.com
    AWS_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY")
    AWS_S3_REGION_NAME = "auto"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    # R2 não suporta ACL; sem isto o django-storages tenta 'public-read' e falha.
    AWS_DEFAULT_ACL = None
    AWS_S3_FILE_OVERWRITE = False
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}

# Build do frontend (Vue/Vite). Em produção o próprio Django serve esses
# arquivos via WhiteNoise: assets em /assets/*, service worker em /sw.js,
# manifest e ícones do PWA na raiz. Em dev a pasta não existe (o Vite serve),
# então o WhiteNoise só é ativado quando o build está presente.
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    WHITENOISE_ROOT = str(FRONTEND_DIST)
    WHITENOISE_INDEX_FILE = True

# Alguns Windows/Pythons não registram esse tipo; sem ele o navegador ignora o
# manifest e não oferece "instalar app".
WHITENOISE_MIMETYPES = {".webmanifest": "application/manifest+json"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "config.pagination.PadraoPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
}


# Logs

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "api": {"format": "[{asctime}] {message}", "style": "{", "datefmt": "%d/%b/%Y %H:%M:%S"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "api"},
        "api_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "api.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "encoding": "utf-8",
            "formatter": "api",
        },
    },
    "loggers": {
        # Chamadas da API (config.logging_middleware) + erros dos apps.
        "api": {"handlers": ["console", "api_file"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console", "api_file"], "level": "INFO", "propagate": False},
        # Sem isto, o traceback de um erro 500 em produção (DEBUG=False) não
        # aparece no log do console/Render — o Django só mandaria pro mail_admins.
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}


# Sentry (rastreamento de erros). Opcional: sem SENTRY_DSN definido, não faz
# nada. Com o DSN, todo erro 500 vai pro painel do Sentry com traceback,
# request e usuário — e dá pra configurar alerta por e-mail.
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
        # Anexa o usuário logado ao erro (app interno, ajuda a reproduzir).
        send_default_pii=True,
        # Só rastreamento de erros; performance/tracing desligado p/ não gastar
        # a cota do plano free.
        traces_sample_rate=0.0,
    )
