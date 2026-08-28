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
- **Mídia efêmera:** fotos e assinaturas ficam no disco do container e **somem a
  cada deploy ou restart**. Para teste de fluxo tudo bem. Para manter:
  - plano Starter + **Disk** (1 GB) montado em `/var/data`, e
    `MEDIA_ROOT=/var/data/media` nas env vars; ou
  - storage S3-compatível (Neon tem buckets) — vale quando virar sistema oficial.
- **Neon free:** o compute do banco também suspende sem uso e religa em ~1 s.

## Atualizações

`git push` na branch `main` → o Render rebuilda e redeploya sozinho
(`autoDeploy: true`). As migrações rodam no build.

## Rodar comandos administrativos

Plano free não tem shell. Uma migração de dados ou comando pontual: adicione ao
final do `render-build.sh`, faça o deploy, e remova depois. Para redefinir a
senha do admin: defina `DJANGO_SUPERUSER_RESET_PASSWORD=1` nas env vars e
redeploy (depois remova a variável).
