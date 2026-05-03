# 0004 - Vercel Frontend Deploy with Split Release Ownership

## Status
Accepted

## Context
Production needs (a) a versioned semver release, (b) a stable production alias on Vercel pointing to the latest blessed deployment, and (c) a manual escape hatch when automation drifts. Mixing these into one workflow has historically caused fake semver-like deploy tags, broken aliases, and ambiguous rollback semantics (PRs #49, #93, #94, #98, #99).

## Decision
Split release responsibilities across three GitHub Actions workflows, each with one job:

| Workflow | Owns |
|----------|------|
| `.github/workflows/frontend.yml` | Runs `semantic-release` on merges to `main` — produces tags + GitHub releases + `CHANGELOG.md` updates. |
| `.github/workflows/cd.yml` | Aliases the latest production deployment to `tedh.gg` via the **Vercel REST API** (not the CLI). Fires on merge to `main`. Requires `VERCEL_TOKEN` (or fallback `VERCEL_API_TOKEN`) and a `VERCEL_SCOPE` repo variable. |
| `.github/workflows/release.yml` | Manual fallback only — never fires on schedule or push. |

Frontend deploys themselves are managed by Vercel's native Git integration (root directory `apps/web/`, region `iad1`, `npm ci` install, `npm run build`).

## Consequences

**Easier**
- Each workflow has one job and one failure mode.
- Manual fallback is preserved without polluting normal CI.
- Vercel REST API gives clearer error signals than `curl`-piped CLI calls (PR #99).

**Harder**
- Three workflows must agree on the same `VERCEL_TOKEN` and project scope.
- A merge to `main` triggers semantic-release **and** the prod alias in parallel — if one races the other, the alias may briefly point at an older deploy.
- `release.yml` requires Node 24+ for the current semantic-release toolchain; running it on older runners breaks (PR #94).

### Cross-Repo Impact
`cedh-research` only.

## Sources
- `apps/web/vercel.json`
- README.md "CI" section
- PR #49 — "ci: checkpoint release and deploy cleanup"
- PR #93 — "fix: simplify CD workflow to alias latest production deployment"
- PR #94 — "fix: restore release aliasing workflows"
- PR #98 — "fix(cd): use Vercel REST API; fire on merge to main"
- PR #99 — "Improve CD workflow diagnostics for Vercel deployment lookup"
