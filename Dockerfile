# syntax=docker/dockerfile:1
# Combined production image: nginx (frontend SPA) + uvicorn (FastAPI backend)
# managed by supervisord.
#
# Build:
#   docker build -t vortex-dl .
#
# Run:
#   docker run -d \
#     -e JWT_SECRET=<secret> \
#     -e SQLALCHEMY_DATABASE_URI=sqlite+aiosqlite:////app/data/app.db \
#     -v vortex-data:/app/data \
#     -v vortex-downloads:/app/downloads \
#     -v vortex-uploads:/app/uploads \
#     -p 80:80 \
#     vortex-dl

# ---------------------------------------------------------------------------
# Stage 1: Build the Vue / Vite frontend
# ---------------------------------------------------------------------------
FROM node:22-alpine AS build-frontend

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

# VITE_BACKEND_URL is intentionally empty: nginx proxies /auth etc. to
# localhost:8000 so the frontend makes same-origin requests.
ARG VITE_BACKEND_URL=""
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Combined runtime (Python 3.12 + nginx + supervisord)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps: curl (health checks), ffmpeg (yt-dlp), nginx, supervisor.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        nginx \
        supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source.
COPY backend/ .

# Copy canonical version so config.py can read it.
COPY VERSION /app/VERSION

# Copy frontend build output to nginx's html root.
COPY --from=build-frontend /app/dist /usr/share/nginx/html

# Copy combined-image runtime config.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/start-backend.sh /app/docker/start-backend.sh
RUN chmod +x /app/docker/start-backend.sh

# Remove the default nginx site to avoid conflicts.
RUN rm -f /etc/nginx/sites-enabled/default

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads /app/data /app/downloads \
    && chown -R appuser:appuser /app /usr/share/nginx/html

# nginx needs to bind port 80 and write to /var/log/nginx.
# Grant appuser access to the necessary directories.
RUN chown -R appuser:appuser /var/log/nginx /var/lib/nginx /run \
    && sed -i 's/user nginx;//' /etc/nginx/nginx.conf \
    || true

USER appuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=20s \
    CMD curl -fsS http://localhost/health || exit 1

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
