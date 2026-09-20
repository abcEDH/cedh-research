# 0024: Vercel Python simulator trial

## Status

Proposed — private proof of concept; not a supported public simulator.

## Context

PR #297 adds a simulator page but has no deployed simulation endpoint. The existing
Next.js deployment cannot invoke the backend CLI without packaging a Python runtime.
Vercel supports native Python functions, so a rewrite is not required to test feasibility.

## Decision

Trial a separate Vercel project rooted at `packages/backend`, using `app.py` and
`vercel.json`. Keep the existing CLI, model artifact, and internal Elo calculations.
Use one worker, exact top-cut propagation, and no prepared-state disk cache.

Require a server-side bearer invite token of at least 32 characters. Fail closed when
configuration is missing. Limit a request to 120 seconds of simulation work and 240
seconds total, leaving headroom below the configured 300-second function duration.
Kill the worker when the stream closes or reaches the deadline. Tokens are never URL
parameters. A per-instance busy gate protects that instance only; it is not a global
rate limit. This is appropriate only for controlled private testing.

The service reads TopDeck and Supabase; it does not ingest data or rebuild Elo.
Do not connect the public simulator page until a deployed preview demonstrates model
loading, authenticated streaming, representative runtime, and cleanup behavior.

## Consequences

Dependency size, cold starts, data-fetch time, and CPU throughput need measurement on
Vercel. A failed or timed-out stream emits an error, never a fabricated completed result.
A deployment can be rolled back independently of tedh.gg. A broader release requires
per-user invitation handling, distributed usage controls, and the web integration.

### Cross-Repo Impact

- Backend owns the Python endpoint and model packaging.
- Web integration remains in PR #297 and must keep TopDeck attribution visible.
- No frontend deployment, ingestion schedule, database schema, or Elo policy changes.

## Sources

- [PR #297](https://github.com/abcEDH/cedh-research/pull/297)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel function limits](https://vercel.com/docs/functions/limitations)
- [Trial runbook](../simulator-vercel-trial.md)
