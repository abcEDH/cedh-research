# cEDH Research

Unified backend ingestion + frontend dashboard for cEDH analytics.

## Structure
- apps/web: Next.js dashboard (App Router, Tailwind, Recharts)
- packages/backend: Python ingestion + analysis + Supabase migrations

## Requirements
- Node.js 20+
- Python 3.12+ (3.14 recommended)

## Environment
Use separate env files for frontend and backend. Do not put server-only keys in frontend env files.
The repo-root `.env` may still be used for local admin/debug scripts, but the Next app only reads `NEXT_PUBLIC_*` variables.

Frontend (`apps/web/.env.local`):
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

Backend (`packages/backend/.env`):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `TOPDECK_API_KEY`

Safe templates live in:
- `./.env.example`
- `apps/web/.env.example`
- `packages/backend/.env.example`

## Frontend (apps/web)
- Dev: `npm run web:dev`
- Build: `npm run web:build`
- E2E: `npm run web:test:e2e`

## Backend (packages/backend)
- Install deps: `npm run backend:install`
- Ingest (example): `python packages/backend/src/ingest.py --days 7 --min-players 32`
- Migrations live in `packages/backend/supabase/migrations/`

## CI
- Frontend workflows run on `apps/web/**` changes
- Backend workflows run on `packages/backend/**` changes
- `ci.yml` provides a tight regression loop for Regional Elo changes:
  - frontend regression tests
  - canonical regional aggregate proof
  - uploaded evidence artifact for human review
- Release ownership: semantic release runs from `.github/workflows/frontend.yml`; production aliasing runs from `.github/workflows/cd.yml`; `.github/workflows/release.yml` remains a manual fallback only

## QA
- Release lessons: `docs/release-lessons-2026-04-05-regional-elo.md`
- QA checklist: `docs/qa-release-checklist.md`

## Contribution Flow
- Review guidance: `CONTRIBUTING.md`
- PRs should use `.github/pull_request_template.md`
- Supported product surfaces live in `docs/supported-surfaces.md`
- After opening a PR and letting CI start, comment `@codex review` for an automated pass
