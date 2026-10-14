# Gazyar — instructions for Claude

Persian (RTL) gas-consumption-optimisation program: FastAPI backend + React subscriber PWA + React staff panel.

**Start every session by reading `HANDOFF.md` (current state + ordered next steps), then `docs/ARCHITECTURE.md`.**
Requirements (R01–R47) and the 3 payment stages are in `ROADMAP.md` (Persian).

- Work on branch `claude/upbeat-keller-0xd6wv`; commit + push after every finished step; update ROADMAP §7 status.
- Backend tests: `cd backend && .venv/bin/python -m pytest -q -p no:warnings` and `scripts/test-backend-pg.sh` (both must pass).
- Frontend checks: `pnpm -r typecheck && pnpm -r test && pnpm lint`. Regenerate API types after backend changes: `node scripts/gen-api.mjs`.
- Never hard-code business numbers (use settings), never write points outside `points.service`, audit every staff mutation, keep `packages/core|motion|data` DOM-free.
- UI text is Persian, `dir=rtl`, Persian digits on output, Jalali dates, no letter-spacing on Persian text.
- The user communicates in Persian; reply in casual Persian.
