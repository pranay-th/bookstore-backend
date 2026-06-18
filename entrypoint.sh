#!/usr/bin/env sh
# entrypoint.sh
#
# Container start-up:
#   1. Apply database migrations (schema must match the deployed code).
#   2. Hand off to the CMD — in production that's supervisord, which runs
#      gunicorn + the Celery worker + Celery beat in one container.
#
# `exec "$@"` makes the CMD (supervisord) PID 1 so it receives signals and
# reaps its child processes. `set -e` aborts the boot if migrations fail, so a
# broken migration never serves traffic against a mismatched schema.
set -e

# Render injects PORT; default to 8000 for local `docker run`.
export PORT="${PORT:-8000}"

echo "[entrypoint] Applying database migrations..."
python manage.py migrate --no-input

echo "[entrypoint] Starting processes (PORT=$PORT)..."
exec "$@"
