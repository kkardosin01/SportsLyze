FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/
COPY packages/cv-pipeline /app/packages/cv-pipeline

RUN pip install --no-cache-dir uv \
    && cd apps/api && uv pip install --system --no-cache -e . \
    && uv pip install --system --no-cache -e /app/packages/cv-pipeline

COPY apps/api /app/apps/api

WORKDIR /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
