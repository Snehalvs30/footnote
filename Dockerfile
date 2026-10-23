# syntax=docker/dockerfile:1
#
# One image for all of Footnote: the React app is built, then served by FastAPI
# alongside the API. Build from the repository root:
#   docker build -t footnote .

# ---- Stage 1: build the React frontend -------------------------------------
# Built natively on the build machine ($BUILDPLATFORM), even when the final image
# targets another CPU: the output is plain HTML/CSS/JS, the same for every CPU.
# This skips slow CPU emulation for the npm build in multi-platform builds.
FROM --platform=$BUILDPLATFORM node:24-slim AS frontend
WORKDIR /frontend
# Dependencies first, so this layer is cached until package-lock.json changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: the Python app -------------------------------------------------
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" \
    FOOTNOTE_EMBEDDING_CACHE_DIR=/app/models \
    FOOTNOTE_STATIC_DIR=/app/static

WORKDIR /app

# Exact package versions from uv.lock, without test tools.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY backend/ ./

# Download the embedding model now, so containers start fast and need no download.
RUN python -c "from app.embeddings import get_embedder; get_embedder()"

COPY --from=frontend /frontend/dist ./static

# Run as an unprivileged user, never as root.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin footnote \
    && chown -R 10001:10001 /app/models
USER 10001:10001

EXPOSE 8000

# Bring the database schema up to date, then serve. exec makes uvicorn the main
# process, so it receives shutdown signals directly. --proxy-headers: trust the
# load balancer's X-Forwarded-* headers (it terminates the connection first).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]