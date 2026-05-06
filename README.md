# tedh.gg

Unified backend ingestion + frontend app for tedh.gg.

## Structure
- apps/web: Next.js dashboard (App Router, Tailwind, Recharts)
- packages/backend: Python ingestion + analysis + Supabase migrations

## Requirements
- Node.js 20+
- Python 3.12+
- just (https://github.com/casey/just) for one-command onboarding

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
Run one command from the repo root:
- `just quickstart`

What it does:
1. Verifies required local commands are available (`node`, `npm`, `python`).
2. Installs JavaScript dependencies with `npm install`.
3. Creates local env files from templates when missing:
   - `.env` from `.env.example`
   - `apps/web/.env.local` from `apps/web/.env.example`
   - `packages/backend/.env` from `packages/backend/.env.example`
4. Installs backend Python dependencies (`npm run backend:install`).
5. Runs repo docs checks (`npm run docs:check` and `npm run docs:hygiene`).

Then start the app with:
- `npm run web:dev`

Notes:
- If you only need frontend setup, run `just quickstart-no-backend` (or `./scripts/quickstart.sh --no-backend`).
- Existing env files are never overwritten.
- Instant spec: `docs/instant-spec-quickstart.md`

## Frontend (apps/web)
- Dev: `npm run web:dev`
- Build: `npm run web:build`
- E2E: `npm run web:test:e2e`

## Backend (packages/backend)
- Install deps: `npm run backend:install`
- Ingest (example): `python packages/backend/src/ingest.py --days 7`
- Migrations live in `packages/backend/supabase/migrations/`

## CI
- Frontend workflows run from `.github/workflows/frontend.yml` on `apps/web/**` changes.
- Backend workflows run from `.github/workflows/ci-backend.yml` on `packages/backend/**` changes.
- Docs checks run from `.github/workflows/docs.yml` for markdown and repo-hygiene validation.
- Frontend verification is centralized in `scripts/verify-frontend.sh`; preview Vercel deployments use `scripts/deploy-frontend-preview.sh` after CI passes.
- Release ownership: semantic release runs from `.github/workflows/frontend.yml`; production aliasing runs from `.github/workflows/cd.yml`; `.github/workflows/release.yml` remains a manual fallback only.
- `cd.yml` expects `VERCEL_TOKEN` (or fallback `VERCEL_API_TOKEN`) plus a `VERCEL_SCOPE` repo/environment variable when the project is under a Vercel team.

## QA
- Release lessons: `docs/release-lessons-2026-04-05-regional-elo.md`
- QA checklist: `docs/qa-release-checklist.md`

## Contribution Flow
- Review guidance: `CONTRIBUTING.md`
- PRs should use `.github/pull_request_template.md`
- Supported product surfaces live in `docs/supported-surfaces.md`
- After opening a PR and letting CI start, comment `@codex review` for an automated pass
