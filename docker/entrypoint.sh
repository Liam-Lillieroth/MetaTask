#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting web process..."

# Defaults (override via docker-compose)
DB_HOST=${DB_HOST:-db}
DB_NAME=${DB_NAME:-mediap}
DB_USER=${DB_USER:-mediap}
DB_PASSWORD=${DB_PASSWORD:-mediap}
SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-0}
COLLECT_STATIC=${COLLECT_STATIC:-1}
APP_DIR=/app

cd "$APP_DIR"

echo "[entrypoint] Waiting for database $DB_HOST ($DB_NAME)..."
attempt=0
until pg_isready -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
  attempt=$((attempt+1))
  if [ $attempt -gt 30 ]; then
    echo "[entrypoint] ERROR: Database not reachable after 60s" >&2
    exit 1
  fi
  sleep 2
done
echo "[entrypoint] Database is ready."

if [ "$SKIP_MIGRATIONS" != "1" ]; then
  echo "[entrypoint] Applying migrations..."
  python manage.py migrate --noinput
else
  echo "[entrypoint] Skipping migrations (SKIP_MIGRATIONS=1)."
fi

if [ "$COLLECT_STATIC" = "1" ]; then
  if [ ! -f .static_collected ]; then
    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput || true
    touch .static_collected || true
  else
    echo "[entrypoint] Static already collected."
  fi
fi

echo "[entrypoint] Launching Gunicorn..."
exec gunicorn --config /app/gunicorn.conf.py mediap.wsgi:application
