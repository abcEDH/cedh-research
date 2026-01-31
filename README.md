# cEDH Research

Unified backend ingestion + frontend dashboard for cEDH analytics.

## Structure
- apps/web: Next.js dashboard (App Router, Tailwind, Recharts)
- packages/backend: Python ingestion + analysis + Supabase migrations

## Requirements
- Node.js 20+
- Python 3.12+ (3.14 recommended)

## Environment
Copy `.env.example` to `.env.local` (frontend) or `.env` (backend as needed) and set:
- SUPABASE_URL
- SUPABASE_SERVICE_KEY
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- TOPDECK_API_KEY

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
