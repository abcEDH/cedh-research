# 0014 - Retire Dead Surfaces Wholesale

## Status
Accepted

## Context
As the product evolved, several surfaces (`/cards`, `/turn-order`, `/survival`) were no longer carrying their weight: the data they exposed was either redundant with other views, no longer accurate, or not used. Leaving them in place created hidden cost — they had routes, tests, docs entries, CI checks validating them, and backend helpers still loading their data. "Soft-archive" patterns (commenting out routes, leaving stub pages, gating behind flags) accumulate cruft and slow review.

## Decision
When a surface is retired, **remove every reference to it in the same change**:
- Frontend route(s) and components
- Tests (unit, contract, E2E)
- Docs entries (including `docs/supported-surfaces.md`)
- CI workflow steps that validate the surface
- Backend helpers/queries that exist only to feed it
- Any data-dictionary entries

Soft-archiving is explicitly discouraged. The CONTRIBUTING guide encodes this:
> "If a surface is retired, remove its code, docs, tests, and CI references together. Prefer deleting dead paths over archiving them in active workflows."

A machine-checkable `docs/supported-surfaces.md` is the source of truth for what exists; CI hygiene checks compare it against the routing tree.

## Consequences

**Easier**
- The codebase reflects what is actually shipped — no archaeological layer.
- Reviewers can trust that every route they see is live.
- New surfaces don't have to step around vestigial helpers.

**Harder**
- Reintroducing a retired surface is a from-scratch effort, not a flag flip.
- A removal PR is wider than a "feature off" PR — more files, more diff, more reviewers.
- Pages-level analytics history for retired surfaces still lives in PostHog but the code doesn't reference it.

### Cross-Repo Impact
`cedh-research` only.

## Sources
- `CONTRIBUTING.md` "Principles" section
- `docs/supported-surfaces.md`
- PR #51 — "refactor: checkpoint retire cards turn-order and survival surfaces"
- `scripts/check-repo-hygiene.mjs` (hygiene gate)
