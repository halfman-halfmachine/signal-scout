# syntax=docker/dockerfile:1

# ── Stage 1: build the Next.js static export ─────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY frontend/ ./
RUN npm run build
# Next static export (output: 'export') emits to /build/out

# ── Stage 2: Python runtime serving API + static export ──────────────────────
FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/data \
    STATIC_DIR=/app/static

# Install backend (deps resolved from pyproject; app/ needed for the build).
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir .

# Bring in the built front-end.
COPY --from=frontend /build/out ./static

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8000

# Simple healthcheck against the API.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
