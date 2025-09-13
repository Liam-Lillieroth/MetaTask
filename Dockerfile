# Production Dockerfile for Django (mediap.wsgi:application)
# Uses entrypoint.sh from the repo to wait for DB, run migrations, collectstatic, then start Gunicorn.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OS deps: netcat for DB wait in entrypoint.sh, build tools if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd build-essential curl \
  && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . /app

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Django settings module per repo CI
ENV DJANGO_SETTINGS_MODULE=mediap.settings

# Expose app port
EXPOSE 8000

# Default command runs your existing entrypoint
CMD ["./entrypoint.sh"]