# Deploy (homologação) — Render + Neon

Um serviço só no Render roda o Django (Gunicorn) **e** serve o frontend Vue
buildado. Banco Postgres no Neon. Frontend e API no mesmo domínio, então não há
CORS nem configuração de URL de API.

```
Navegador ─┬─ /                 → index.html (SPA Vue)
           ├─ /assets/*, /sw.js → WhiteNoise (build do Vite)
           ├─ /api/*            → Django REST Framework
           ├─ /admin/*          → Django admin
           └─ /media/*          → uploads (disco do serviço)
                    │
              Gunicorn (Render Web Service)
                    │
              Postgres (Neon)
```

## 1. Subir o código pro GitHub

```bash
git add -A
git commit -m "Configura deploy no Render"
# crie um repositório vazio em https://github.com/new (sem README)
git remote add origin https://github.com/<voce>/gestor-servicos.git
git branch -M main
git push -u origin main
```

## 2. Criar o serviço no Render

1. https://dashboard.render.com → **New +** → **Blueprint**.
2. Conecte o repositório. O Render acha o `render.yaml` e mostra o serviço
   `gestor-servicos`.
3. Antes de **Apply**, preencha as variáveis marcadas como *sync: false*:

   | Variável | Valor |
   |---|---|
   | `DATABASE_URL` | string **pooled** do Neon, terminando em `?sslmode=require` |
   | `DJANGO_SUPERUSER_USERNAME` | ex. `edison` |
   | `DJANGO_SUPERUSER_PASSWORD` | senha forte |
   | `DJANGO_SUPERUSER_EMAIL` | seu e-mail |

   `DATABASE_URL` do projeto Neon `gestor-servicos`:
   Dashboard Neon → Connection Details → **Pooled connection**.

4. **Apply**. O primeiro build leva ~3–5 min (instala Node+Python, builda o
   Vite, `collectstatic`, `migrate`, cria o superusuário).

## 3. Acessar

- App: `https://gestor-servicos.onrender.com`
- Admin: `https://gestor-servicos.onrender.com/admin/`

Login com o superusuário. No admin, cadastre os funcionários (papel: técnico /
gestor / RH) e a jornada de trabalho de cada um.

## 4. Instalar o PWA no celular

Abra a URL no Chrome (Android) ou Safari (iOS) → menu → **Instalar aplicativo** /
**Adicionar à Tela de Início**. Como o domínio é fixo, o app instalado continua
funcionando entre deploys.

## Limitações do plano free (aceitáveis p/ homologação)

- **Cold start:** o serviço hiberna após ~15 min sem acesso; a primeira
  requisição depois disso demora ~50 s. Some com o plano **Starter** (US$7/mês).
- **Mídia:** com o Cloudflare R2 configurado (abaixo), fotos e assinaturas
  persistem. Sem R2, ficam no disco do container e **somem a cada deploy**.
- **Neon free:** o compute do banco também suspende sem uso e religa em ~1 s.

## Fotos e assinaturas — Cloudflare R2

O disco do Render (plano free) é apagado a cada deploy. As imagens vão para um
bucket R2 (grátis até 10 GB). O bucket é **privado** — as imagens continuam
sendo servidas em `/media/...` pela própria API (proxy do bucket), então nada
muda no frontend e o cache offline do PWA segue funcionando.

1. **Cloudflare** → painel → **R2** → *Create bucket* (nome ex. `gestor-servicos-media`).
2. R2 → *Manage R2 API Tokens* → *Create API token* → permissão **Object Read & Write**,
   escopo neste bucket. Anote **Access Key ID**, **Secret Access Key** e o
   **endpoint** (`https://<accountid>.r2.cloudflarestorage.com`).
3. No Render, nas variáveis de ambiente:

   | Variável | Valor |
   |---|---|
   | `R2_BUCKET` | `gestor-servicos-media` |
   | `R2_ENDPOINT` | `https://<accountid>.r2.cloudflarestorage.com` |
   | `R2_ACCESS_KEY_ID` | (token) |
   | `R2_SECRET_ACCESS_KEY` | (token) |

4. Redeploy. A partir daí todo upload novo vai pro R2. Fotos enviadas antes
   disso (que já estavam no disco efêmero) continuam 404 — reenvie ou descarte
   as OS de teste.

## Logs e erros

- **Log ao vivo:** painel do Render → serviço `gestor-servicos` → aba **Logs**.
  Mostra tudo que o app imprime: cada chamada da API (`METHOD /api/... → status
  (ms) [usuário]`, do `APILoggingMiddleware`), tracebacks de erro 500 e o
  Gunicorn. O plano free guarda só um buffer recente.
- **Rastreamento de erros (Sentry) — opcional mas recomendado:**
  1. Conta grátis em https://sentry.io → **Create Project** → plataforma
     **Django**.
  2. Copie o **DSN** (`https://...@o0.ingest.sentry.io/0`).
  3. No Render, variável `SENTRY_DSN` = esse DSN → redeploy.
  4. A partir daí todo erro 500 aparece no Sentry com traceback, dados da
     requisição e usuário logado. Dá pra ativar alerta por e-mail em
     *Settings → Alerts*.
  - Sem `SENTRY_DSN` definido, o Sentry fica desligado e não pesa em nada.

## Atualizações

`git push` na branch `main` → o Render rebuilda e redeploya sozinho
(`autoDeploy: true`). As migrações rodam no build.

## Rodar comandos administrativos

Plano free não tem shell. Uma migração de dados ou comando pontual: adicione ao
final do `render-build.sh`, faça o deploy, e remova depois. Para redefinir a
senha do admin: defina `DJANGO_SUPERUSER_RESET_PASSWORD=1` nas env vars e
redeploy (depois remova a variável).
