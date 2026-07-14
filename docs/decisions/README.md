# Architectural Decision Records

This directory captures load-bearing decisions about how `cedh-research` (tedh.gg) is structured. Format follows [MADR](https://adr.github.io/madr/) with explicit cross-repo impact.

These ADRs were extracted retroactively on 2026-05-03 from git history, merged PRs, README/CONTRIBUTING, and configuration files. Each one cites the evidence it was derived from.

## Index

| #  | Title | Status | Affected | Evidence |
|----|-------|--------|----------|----------|
| [0001](0001-hybrid-ts-python-monorepo.md) | Hybrid TypeScript + Python Monorepo | Accepted | repo root | `package.json`, `packages/backend/pyproject.toml` |
| [0002](0002-nextjs-app-router-react-19-stack.md) | Next.js App Router + React 19 + Tailwind v4 Web Stack | Accepted | `apps/web/` | `apps/web/package.json`, PR #59 |
| [0003](0003-supabase-as-system-of-record.md) | Supabase (Postgres) as System of Record | Accepted | `apps/web/`, `packages/backend/` | 51 migrations, PR #55, #117 |
| [0004](0004-vercel-deploy-and-release-ownership.md) | Vercel Frontend Deploy with Split Release Ownership | Accepted | `.github/workflows/`, `apps/web/` | PRs #49, #93, #94, #98, #99 |
| [0005](0005-read-model-pattern.md) | Persisted Read Models Over Request-Time Computation | Accepted | `apps/web/`, `packages/backend/` | PRs #133, #134, #145, #154 |
| [0006](0006-page-level-caching-with-unstable-cache.md) | Page-Level Caching with Next.js `unstable_cache` | Accepted | `apps/web/` | PRs #116, #118, #122 |
| [0007](0007-split-cron-pipelines.md) | Split Scheduled Ingestion and Elo Maintenance Pipelines | Accepted | `.github/workflows/` | PRs #54, #80, #117, #120 |
| [0008](0008-manual-only-elo-maintenance.md) | Elo Maintenance Is Manual-Only | Accepted | `.github/workflows/ci-backend-maintenance.yml` | PRs #82, #89 |
| [0009](0009-tedh-gg-production-domain.md) | Production Domain is `tedh.gg` | Accepted | `apps/web/`, `.github/workflows/cd.yml` | PRs #121, #123 |
| [0010](0010-lockfile-policy.md) | Lockfile-Enforced Reproducible Installs | Accepted | repo root, `apps/web/`, `packages/backend/` | `CONTRIBUTING.md`, PR #104 |
| [0011](0011-posthog-for-product-analytics.md) | PostHog for Product Analytics and Error Capture | Accepted | `apps/web/` | PR #156 |
| [0012](0012-ai-review-is-advisory.md) | AI Code Review Is Advisory; Humans Approve Merges | Accepted | review process | `CONTRIBUTING.md`, PR #156 declined-suggestion thread |
| [0013](0013-topdeck-attribution-and-compliance.md) | TopDeck Attribution and API Compliance | Accepted | `apps/web/`, `packages/backend/` | PR #53 |
| [0014](0014-retire-dead-surfaces-wholesale.md) | Retire Dead Surfaces Wholesale | Accepted | repo-wide | `CONTRIBUTING.md`, PR #51, `docs/supported-surfaces.md` |
| [0016](0016-rank-activity-window-and-topdeck-snapshot-pruning.md) | Rank Activity Window and TopDeck Snapshot Pruning | Accepted | `packages/backend/` | PR #263, issue #252 |

## How decisions cluster

- **Data flow:** 0003 → 0005 → 0006 (Supabase → persisted read models → cached at the edge). Mutations to one usually require touching the next.
- **Operations:** 0007 → 0008 (split pipelines + manual-only Elo). Define what runs where and when.
- **Release path:** 0004 → 0009 (Vercel + tedh.gg). How code reaches users.
- **Hygiene posture:** 0001 → 0010 → 0014 (monorepo shape, lockfiles, dead-path removal). How the repo stays maintainable.
- **External integration:** 0011 → 0013 (PostHog out, TopDeck in). Third-party contracts.
- **Process:** 0012 (AI review). Who and what approves merges.

## Ownership (last 90 days)

Derived from `git log --since="90 days ago"` per area. Use as a starting point — full ownership lives in `.github/CODEOWNERS` if/when it is added.

| Area | Primary committer(s) |
|------|----------------------|
| `apps/web/` | marsteralex, vem |
| `packages/backend/` | marsteralex, vem |
| `.github/workflows/` | Victor Em (vem), marsteralex |
| `packages/backend/supabase/migrations/` | vem, Victor Em |
| `docs/` | marsteralex, vem |
| `scripts/` (repo hygiene) | Victor Em |

> Note: "vem" and "Victor Em" are the same git identity with different `user.name` configs.

## Adding a new ADR

1. Pick the next free integer (e.g. `0015`).
2. Use MADR template — `Status`, `Context`, `Decision`, `Consequences` (with `### Cross-Repo Impact`), `Sources`.
3. Cite at least one PR, commit, or doc that made the decision concrete.
4. Add a row to the index table above.
5. If this decision supersedes an older one, mark the older one `Superseded by NNNN` and link both ways.

## Why these and not others?

ADRs are for **load-bearing** choices — the ones that, if reversed, would force coordinated changes across multiple files, services, or workflows. We deliberately did **not** make ADRs for:

- Library upgrades that didn't change usage shape (e.g. minor Recharts versions).
- Refactor PRs that extracted shared utilities (formatPct, normalizeDateKey, etc.) — code-level cleanup, not architecture.
- Per-page UI polish or copy changes.
- Cache-key bumps when the read-model shape evolved (those are noted in ADR 0005/0006 as a recurring pattern, not their own decisions).

If a future change feels like it should have an ADR but doesn't fit, prefer adding one over leaving it implicit. Cheap to write, expensive to recover later.
