FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./

# Sentry sourcemap upload + release injection run at BUILD time via
# @sentry/vite-plugin, which reads these from the build env. Railway passes
# service variables into a Dockerfile build ONLY for vars declared as ARG here;
# without these lines `npm run build` sees none of them and the plugin silently
# skips (no sourcemaps, no release). We pass them INLINE to the build process
# (not via ENV) so the auth token is never persisted in an image layer. All are
# optional — the build still succeeds and just skips upload when absent.
ARG SENTRY_AUTH_TOKEN
ARG SENTRY_ORG
ARG SENTRY_PROJECT
ARG SENTRY_RELEASE
ARG RAILWAY_GIT_COMMIT_SHA
RUN SENTRY_AUTH_TOKEN="$SENTRY_AUTH_TOKEN" \
    SENTRY_ORG="$SENTRY_ORG" \
    SENTRY_PROJECT="$SENTRY_PROJECT" \
    SENTRY_RELEASE="$SENTRY_RELEASE" \
    RAILWAY_GIT_COMMIT_SHA="$RAILWAY_GIT_COMMIT_SHA" \
    npm run build

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
# FORWARDED_ALLOW_IPS controls which immediate-peer addresses uvicorn trusts the
# X-Forwarded-For header from (for deriving request.client.host, which the per-IP
# rate limiter keys on). Default "127.0.0.1" reproduces uvicorn's own default, so
# behaviour is unchanged unless the env var is set. Set it to the specific Railway
# edge-proxy hop ONCE that hop is verified from prod `client_ip=` logs — NEVER "*"
# (that trusts XFF from any peer and lets clients spoof their IP to evade the
# limiter). See docs/deployment.md § Rate-limiter operational notes & findings.
CMD ["/bin/sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --forwarded-allow-ips \"${FORWARDED_ALLOW_IPS:-127.0.0.1}\""]