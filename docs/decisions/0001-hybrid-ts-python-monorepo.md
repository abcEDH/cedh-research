# 0001 - Hybrid TypeScript + Python Monorepo

## Status
Accepted

## Context
The product needs both a public-facing read-heavy web app and a data ingestion / analytics pipeline. The web app is naturally TypeScript (Next.js, React, Supabase JS). The ingestion pipeline pulls from external APIs (TopDeck), normalizes structured data, runs analytics, and writes back to Supabase — that work has historically been Python.

Forcing both into a single language adds friction at the dependency-management layer (npm cannot manage Python deps; pip/uv cannot manage Node deps), but keeping them in separate repos creates coordination cost: schema migrations, environment shape, CI rules, and release cadence are tightly coupled.

## Decision
Use a single monorepo with two top-level work units:
- `apps/web/` — Next.js TypeScript application, registered as the only npm workspace at the root `package.json` (`"workspaces": ["apps/web"]`).
- `packages/backend/` — Python project managed by `uv`, with `pyproject.toml`, `uv.lock`, and `requirements.txt`. Deliberately **not** an npm workspace.

Cross-cutting infrastructure (Supabase migrations, GitHub Actions workflows, repo-wide hygiene scripts) lives at the root.

## Consequences

**Easier**
- Schema changes and the consumers of those schemas land in one PR.
- Shared docs (`docs/`, `CONTRIBUTING.md`) describe the whole system.
- `just quickstart` can bootstrap both halves from one command.

**Harder**
- Two dependency systems must be installed locally (Node 20+ AND Python 3.12+).
- CI must split workflows by language to avoid running unrelated jobs (see ADR 0010).
- Tooling that assumes a uniform monorepo (e.g. Nx, Turborepo) is not a clean fit.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- `package.json` workspaces declaration
- `packages/backend/pyproject.toml`
- `README.md` "Structure" section
- `CONTRIBUTING.md` "Local Setup"
