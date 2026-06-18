#!/usr/bin/env sh
# entrypoint.sh
#
# Container start-up: apply database migrations before serving so the schema
# always matches the deployed code, then hand off to the CMD (gunicorn).
#
# Using `exec "$@"` makes gunicorn PID 1 so it receives signals (graceful
# shutdown) directly. `set -e` aborts the boot if migrations fail, so a broken
# migration never serves traffic against a mismatched schema.
set -e

echo "[entrypoint] Applying database migrations..."
python manage.py migrate --no-input

echo "[entrypoint] Starting application..."
exec "$@"
