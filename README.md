# Gestor de Serviços

App interno para unificar dois sistemas usados hoje na empresa:

- **Ordens de Serviço** (hoje no Auvo) — abertura pelo técnico ou pelo gestor, escolha de cliente já cadastrado (ou cadastro na hora), localização de abertura, execução em campo, fotos e assinatura do cliente.
- **Ponto eletrônico** (hoje no Secullum RH) — bater ponto com mapa de localização em tempo real, endereço por geocodificação reversa, funcionamento offline, cartão de ponto mensal com saldo (extra/faltante) baseado na jornada de cada funcionário, indicadores de horas extras/faltantes, e solicitações de ajuste/justificativa de ausência com aprovação do gestor.

PWA instalável, pensado para os técnicos que hoje usam o Auvo em campo.

## Stack

- **Backend:** Django + Django REST Framework + PostgreSQL (SQLite em dev), autenticação JWT.
- **Frontend:** Vue 3 + Vite, PWA (service worker via `vite-plugin-pwa`), fila de sincronização offline para ponto, mapas via Leaflet/OpenStreetMap.

## Rodando localmente

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt   # Windows
cp .env.example .env
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py createsuperuser
venv\Scripts\python manage.py runserver
```

API em `http://127.0.0.1:8000`, admin em `/admin/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App em `http://localhost:5173` (proxy automático de `/api` e `/media` para o backend).

## Estado atual

- [x] Login (JWT), papéis (técnico/gestor/RH/admin)
- [x] Ordens de Serviço: criar (técnico ou gestor), buscar/cadastrar cliente na hora, "estou no local" (geolocalização de abertura), iniciar/concluir, fotos, assinatura do cliente
- [x] Ponto: bater ponto com mapa ao vivo + endereço, fila offline, jornada de trabalho por funcionário (até 2 períodos, configurada pelo RH no admin)
- [x] Cartão Ponto (mês a dia, saldo extra/faltante) e Indicadores (gráficos de horas extras/faltantes)
- [x] Solicitações de ajuste de ponto / justificativa de ausência, com aprovação do gestor
- [x] Notificações in-app (sino no topo) quando uma OS é atribuída ou uma solicitação é analisada
- [x] Painel do gestor: status de ponto dos técnicos hoje, OS em aberto, solicitações pendentes
- [x] Exportar/imprimir o Cartão Ponto (via impressão do navegador → salvar como PDF)
- [x] Comprovante de atendimento por OS (PDF): no Painel do Gestor, seção "Comprovantes de OS" com filtro por mês/técnico → abre a OS num layout de impressão com dados, relato, fotos e assinatura

## O que ainda falta antes de virar o sistema oficial

- Confirmar com RH/jurídico se o ponto deste app poderá ser o registro oficial (Portaria 671/2021) ou se roda em paralelo com o Secullum no início.
- Jornada de trabalho hoje é única para todos os dias úteis (sem variação por dia da semana nem feriados).
- Notificações são só "in-app" (checadas a cada 60s com o app aberto), não notificação push do sistema operacional.

## Deploy em produção

1. **Banco de dados:** provisionar PostgreSQL no servidor da empresa (não usar SQLite em produção).
2. **Variáveis de ambiente:** copiar `backend/.env.production.example` para `backend/.env` no servidor e preencher com valores reais (gerar uma `SECRET_KEY` nova, nunca reaproveitar a de exemplo).
3. **Dependências e migração:**
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```
4. **Servir o backend com Gunicorn** (já está no `requirements.txt`):
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```
5. **Build do frontend** e servir os arquivos estáticos por um Nginx (ou similar) na frente do Gunicorn:
   ```bash
   cd frontend && npm run build
   ```
   O resultado fica em `frontend/dist/` — aponte o Nginx pra servir esses arquivos e fazer proxy de `/api` e `/media` para o Gunicorn.
6. **HTTPS obrigatório** — necessário para a geolocalização funcionar no navegador/celular. Depois de confirmar que o HTTPS está funcionando corretamente, considerar ativar HSTS (`SECURE_HSTS_SECONDS` no `settings.py`) — não vem ativado por padrão para evitar bloquear usuários caso o HTTPS tenha algum problema no início.
7. **Backup:** configurar `pg_dump` periódico do banco e backup da pasta `media/` (fotos e assinaturas ficam lá, não no banco).
