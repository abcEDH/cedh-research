# 0010 - Lockfile-Enforced Reproducible Installs

## Status
Accepted

## Context
The repo contains both a JavaScript and a Python project. CI must produce identical environments to the developer's machine to avoid "works on my laptop" regressions. Without enforced lockfiles, npm and pip resolve transitive dependencies opportunistically, producing drift between local and CI installs.

## Decision

**Frontend (`apps/web/`)**
- `package-lock.json` is committed.
- All CI jobs use `npm ci` (never `npm install`).
- Dependency changes require both `package.json` and `package-lock.json` updates in the same commit.

**Backend (`packages/backend/`)**
- `uv.lock` is committed.
- CI installs from `uv.lock` (lockfile-enforced).
- `pyproject.toml` defines deps; `uv` resolves and locks them.
- A `[dependency-groups.dev]` group separates dev tooling (pytest, ruff, mypy, types-*) from runtime deps.
- A legacy `requirements.txt` is also retained for environments that don't speak `uv`.

## Consequences

**Easier**
- CI installs are deterministic and fast (no network resolution).
- Bisecting a regression caused by a dep upgrade is feasible because the lockfile change is in git history.

**Harder**
- Two lockfile workflows to teach contributors (`npm ci` vs `uv` semantics).
- Maintaining both `pyproject.toml` and `requirements.txt` is mild duplication.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- `CONTRIBUTING.md` "Dependency Lockfile Policy"
- `apps/web/vercel.json` (`"installCommand": "npm ci"`)
- `packages/backend/uv.lock`
- `packages/backend/pyproject.toml`
- PR #104 — "ci: enforce lockfile for Python deps, add dev group to pyproject.toml"
