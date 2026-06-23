#!/bin/sh
set -e

cd /app/backend

echo "Starting Invoice App..."

echo "Checking database migration status..."
python -m alembic current || true

echo "Applying Alembic migrations..."
python -m alembic upgrade head

echo "Starting FastAPI with Gunicorn..."
exec gunicorn \
    app.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 180 \
    --access-logfile - \
    --error-logfile -
