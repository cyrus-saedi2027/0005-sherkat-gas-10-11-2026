#!/usr/bin/env bash
# Fresh, seeded backend for Playwright (port 8000). Each run starts from the same demo data.
set -euo pipefail
cd "$(dirname "$0")/../backend"
DATA="${E2E_DATA_DIR:-/tmp/gazyar-e2e}"
rm -rf "$DATA" && mkdir -p "$DATA"
export GAZYAR_ENV=dev GAZYAR_DATABASE_URL="sqlite:///$DATA/e2e.db" GAZYAR_UPLOAD_DIR="$DATA/uploads" GAZYAR_EXPOSE_DEV_OTP=true
. .venv/bin/activate
python -m app.cli seed --demo >/dev/null
exec uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning
