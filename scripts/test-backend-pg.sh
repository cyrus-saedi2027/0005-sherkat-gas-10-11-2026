#!/usr/bin/env bash
# Run the backend suite against PostgreSQL 16 (second database layer, docs/TESTING.md).
set -euo pipefail
cd "$(dirname "$0")/../backend"
if ! pg_isready -q -h localhost -p 5432 2>/dev/null; then
  (pg_ctlcluster 16 main start || sudo -u postgres pg_ctlcluster 16 main start) >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do pg_isready -q -h localhost -p 5432 && break; sleep 0.5; done
fi
su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='gazyar'\"" | grep -q 1 || \
  su postgres -c "psql -c \"CREATE ROLE gazyar LOGIN PASSWORD 'gazyar' CREATEDB\"" >/dev/null
su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='gazyar_test'\"" | grep -q 1 || \
  su postgres -c "createdb -O gazyar gazyar_test"
. .venv/bin/activate
GAZYAR_TEST_DATABASE_URL="postgresql+psycopg://gazyar:gazyar@localhost:5432/gazyar_test" python -m pytest tests -q -p no:warnings "$@"
