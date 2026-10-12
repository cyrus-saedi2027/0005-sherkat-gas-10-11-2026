# Testing — layers and how to run them

| Layer | Command | What it proves |
|---|---|---|
| Backend unit + API + permission matrix + security | `cd backend && .venv/bin/python -m pytest` | business rules, every role × endpoint, no enumeration, rate limits, upload validation, idempotent rewards |
| Same suite on PostgreSQL 16 | `scripts/test-backend-pg.sh` | no SQLite-only behaviour (caught a 64-char column and a WAL snapshot issue) |
| Migrations | `alembic upgrade head && alembic check && alembic downgrade base` | schema matches models, reversible |
| Lint | `cd backend && .venv/bin/ruff check app tests` · `pnpm lint` | |
| Shared contract | `packages/core/fixtures/normalize.json` is loaded by **both** pytest and vitest | Persian/Arabic digit + mobile + national-code + IBAN normalisation identical on client and server |
| Frontend unit/component | `pnpm -r test` · `pnpm -r typecheck` | validators, Jalali, API client refresh logic, spring engine, components |
| End-to-end | `pnpm e2e` (Playwright, real backend + both apps) | user and staff journeys on phone and desktop viewports |

Rules: every module ships tests in the same change; after each module the **whole** suite runs again
(regression) on SQLite and PostgreSQL; a red suite blocks the next module.
