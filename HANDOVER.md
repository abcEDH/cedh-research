# HANDOVER.md

## Current Branch
`fix/backend-pr-ci-gates`

## Active Changes
Modified files (uncommitted):
- `apps/web/src/app/commanders/[id]/page.tsx`
- `apps/web/src/app/commanders/page.tsx`
- `apps/web/src/app/commanders/trends/page.tsx`
- `apps/web/src/app/page.tsx`
- `packages/backend/src/rebuild_global_elo_tables.py`

New untracked files:
- `.claude/`
- `packages/backend/check_schema.py`
- `packages/backend/check_topdeck_table.py`
- `packages/backend/supabase/migrations/20260501000000_regional_elo_leaderboard_topdeck_fields.sql`

## Recent Commits
| Commit | Description |
|--------|-------------|
| 03fd3c2 | test(web): align commanders-cache assertions with suspense-split page |
| 6f33585 | fix(web): suspense-split /commanders so heading renders on first byte |
| 8ee2b80 | ci: stop gating migrations on data dictionary |
| cbc0c40 | [codex] Reduce regional Elo read cost (#126) |

## Context
Working on backend PR CI gates - likely modifying CI configuration to not require data dictionary checks for backend-only changes.
