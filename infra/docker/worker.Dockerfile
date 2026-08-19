FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/worker/pyproject.toml apps/worker/
COPY packages/cv-pipeline /app/packages/cv-pipeline

RUN pip install --no-cache-dir uv \
    && cd apps/worker && uv pip install --system --no-cache -e . \
    && uv pip install --system --no-cache -e /app/packages/cv-pipeline

COPY apps/worker /app/apps/worker

WORKDIR /app/apps/worker

CMD ["celery", "-A", "src.celery_app", "worker", "--loglevel=info"]
