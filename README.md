# cEDH Research

Unified backend ingestion + frontend dashboard for cEDH analytics.

## Structure
- apps/web: Next.js dashboard (App Router, Tailwind, Recharts)
- packages/backend: Python ingestion + analysis + Supabase migrations

## Requirements
- Node.js 20+
- Python 3.12+

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

## Quick Start
1. Install prerequisites: Node.js 20+ and Python 3.12+.
2. Install JavaScript dependencies from repo root:
   - `npm install`
3. Copy environment templates and fill in required values:
   - `cp .env.example .env`
   - `cp apps/web/.env.example apps/web/.env.local`
   - `cp packages/backend/.env.example packages/backend/.env`
4. Start the web app:
   - `npm run web:dev`
5. (Optional) Install backend Python dependencies:
   - `npm run backend:install`
6. Validate docs and repo hygiene before opening or reviewing a PR:
   - `npm run docs:check`
   - `npm run docs:hygiene`

## Frontend (apps/web)
- Dev: `npm run web:dev`
- Build: `npm run web:build`
- E2E: `npm run web:test:e2e`

## Backend (packages/backend)
- Install deps: `npm run backend:install`
- Ingest (example): `python packages/backend/src/ingest.py --days 7 --min-players 32`
- Migrations live in `packages/backend/supabase/migrations/`

## CI
- Frontend workflows run from `.github/workflows/frontend.yml` on `apps/web/**` changes.
- Backend workflows run from `.github/workflows/ci-backend.yml` on `packages/backend/**` changes.
- Docs checks run from `.github/workflows/docs.yml` for markdown and repo-hygiene validation.
- Release ownership: semantic release runs from `.github/workflows/frontend.yml`; production aliasing runs from `.github/workflows/cd.yml`; `.github/workflows/release.yml` remains a manual fallback only.

## QA
- Release lessons: `docs/release-lessons-2026-04-05-regional-elo.md`
- QA checklist: `docs/qa-release-checklist.md`

## Contribution Flow
- Review guidance: `CONTRIBUTING.md`
- PRs should use `.github/pull_request_template.md`
- Supported product surfaces live in `docs/supported-surfaces.md`
- After opening a PR and letting CI start, comment `@codex review` for an automated pass
