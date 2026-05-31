# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps kept minimal; ffmpeg is required by yt-dlp for audio extraction.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads /app/data /app/downloads \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Apply migrations, then launch the API. Uses the wrapper entrypoint so the
# container is self-bootstrapping on first run.
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
