FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

ENV FRONTEND_DIST_DIR=/app/frontend/dist

# Run as a non-root user.  The sandbox subprocess inherits this UID, so even if
# the AST guard is bypassed the escaped process has no write access to / and
# cannot bind privileged ports or modify app files.  The app itself only needs
# write access to /tmp (for the harness subprocess) which is world-writable.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

# Railway injects PORT at runtime; fall back to 8000 for local docker runs.
CMD ["/bin/sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]