#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: backend/scripts/grant_plan.sh <email> <pro|elite>

Reads ADMIN_SECRET from backend/.env, then grants the requested plan override.

Environment overrides:
  BASE_URL    Target app origin (default: https://datathink.co)
  GRANT_DAYS  Override duration in days (default: 60)
EOF
  exit 2
}

email="${1:-}"
plan="${2:-}"

if [ -z "$email" ] || [ -z "$plan" ]; then
  usage
fi

case "$plan" in
  pro|elite) ;;
  *)
    echo "error: tier must be 'pro' or 'elite'." >&2
    exit 2
    ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
env_file="$repo_root/backend/.env"

if [ ! -f "$env_file" ]; then
  echo "error: missing env file at $env_file" >&2
  exit 1
fi

admin_secret="$(grep '^ADMIN_SECRET=' "$env_file" | cut -d= -f2-)"
if [ -z "$admin_secret" ]; then
  echo "error: ADMIN_SECRET is not set in $env_file" >&2
  exit 1
fi

base_url="${BASE_URL:-https://datathink.co}"
grant_days="${GRANT_DAYS:-60}"

case "$grant_days" in
  ''|*[!0-9]*)
    echo "error: GRANT_DAYS must be a positive integer." >&2
    exit 2
    ;;
esac

if [ "$grant_days" -lt 1 ] || [ "$grant_days" -gt 365 ]; then
  echo "error: GRANT_DAYS must be between 1 and 365." >&2
  exit 2
fi

curl -sS -X POST "$base_url/api/admin/grant-plan" \
  -H "Authorization: Bearer $admin_secret" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$email\",\"plan\":\"$plan\",\"days\":$grant_days}"
