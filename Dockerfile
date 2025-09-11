FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential libpq-dev postgresql-client curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# Create runtime dirs
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && addgroup --system django && adduser --system --ingroup django django \
    && chown -R django:django /app

USER django

EXPOSE 8000

# Ensure entrypoint scripts are executable
RUN chmod +x docker/entrypoint.sh docker/healthcheck.sh || true

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "mediap.wsgi:application"]