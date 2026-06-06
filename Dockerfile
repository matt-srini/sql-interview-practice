FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime

WORKDIR /app/backend

# libseccomp2: the shared library that pyseccomp (ctypes) binds to for the
# sandbox egress filter. Without it the filter no-ops (fail-open).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libseccomp2 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

ENV FRONTEND_DIST_DIR=/app/frontend/dist
# App-wide: no .pyc writes. The app process runs as non-root appuser and /app is
# root-owned (read-only to appuser), so a bytecode-cache write would fail anyway;
# disabling it avoids the attempt and keeps the app dir effectively immutable.
ENV PYTHONDONTWRITEBYTECODE=1

# Run as a non-root user. /app is deliberately left ROOT-OWNED (we do NOT chown it
# to appuser): appuser can read + execute the app but CANNOT WRITE it. So a sandbox
# escape (same UID) cannot drop a backdoor into app code or overwrite a module —
# the app directory is effectively read-only at runtime. The only writable path the
# sandbox needs is /tmp (world-writable). This is the in-image equivalent of a
# --read-only root filesystem, which Railway's managed platform does not expose.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8000

# Railway injects PORT at runtime; fall back to 8000 for local docker runs.
CMD ["/bin/sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]