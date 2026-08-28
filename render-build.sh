#!/usr/bin/env bash
# Build do Render: frontend (Vite) + backend (Django), num serviço só.
set -o errexit

echo "==> [1/4] Build do frontend (Vite)"
cd frontend
npm ci
npm run build
cd ..

echo "==> [2/4] Dependências do backend"
pip install -r backend/requirements.txt

echo "==> [3/4] collectstatic + migrate"
python backend/manage.py collectstatic --no-input
python backend/manage.py migrate --no-input

echo "==> [4/4] Superusuário (se DJANGO_SUPERUSER_* estiverem definidas)"
python backend/manage.py bootstrap_admin
