FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps needed by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run collectstatic at build time using a dummy SECRET_KEY and a stub DATABASE_URL.
# collectstatic does not need a real DB or real secrets — it only needs Django to load.
# The real DATABASE_URL and SECRET_KEY are injected by Render at runtime.
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=postgresql://placeholder:placeholder@placeholder:5432/placeholder \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    python manage.py collectstatic --no-input

# Migrations run on container start via the entrypoint (before the CMD), so the
# schema always matches the deployed code.
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# The entrypoint migrates, then execs the CMD. supervisord runs gunicorn +
# the Celery worker + Celery beat together in this single container.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["supervisord", "-c", "/app/supervisord.conf"]
