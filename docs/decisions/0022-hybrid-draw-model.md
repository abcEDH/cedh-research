# 0022 — Hybrid draw model with internal Elo winner probabilities

## Status

Accepted.

## Context

PR #295 packages the v4 draw artifact and shared simulation paths. The prior
branch also included a Next.js handler spawning Python without a deployable
backend runtime or access controls. Internal Elo parameters have since been
versioned by ADR 0021.

## Decision

Use the v4 artifact's draw class and the shared internal Elo model for conditional
winner probabilities. Exclude displayed TopDeck Elo from the default artifact's
features. Pin scikit-learn to its training version, 1.7.2, and test real artifact
inference. Resolve the pickle's unqualified Cython loss module in a scoped loader.

Keep backend CLI streaming, but defer the web endpoint to PR #297 until its
Python service deployment, access controls, and concurrency limits are ready.

Keep exact seeded Top 16/10/4 propagation. A five-player Swiss field uses one
four-player pod and one bye; repeat avoidance is capped at 32 pods.

## Consequences

Draw forecasts change; the versioned Elo parameters and rebuilt database do not.
Future scikit-learn upgrades must migrate or retrain the artifact and verify
prediction parity. Loading pickle files remains restricted to trusted artifacts.

### Cross-Repo Impact

No new web route or database migration ships with this decision. The backend
lockfile and Python runtime must remain aligned with the tracked model.

## Sources

- https://github.com/abcEDH/cedh-research/pull/295
- [ADR 0021](0021-tuned-internal-elo.md)
