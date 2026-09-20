# Private simulator Vercel trial

This endpoint is a proof of concept for PR #297, not a public tedh.gg route.
See [ADR 0024](decisions/0024-vercel-python-simulator-trial.md).

## Deployment

Create a separate Vercel project with root `packages/backend` and FastAPI preset.
Use Python 3.12, Fluid Compute, and the committed 300-second maximum duration.
The lockfile owns dependencies. Keep automatic Git deployments disconnected for the trial. `.vercelignore` excludes the legacy requirements
file, local environments, credentials, datasets, tests, and migrations. The curated
commander, region, and tournament-location lookup JSON files remain included because CLI imports need them. The trusted
v4 model under `models/pod-outcome/v4` must be included.

Configure these **server-only** environment variables for the private preview:

- `SIMULATOR_INVITE_TOKEN`: a cryptographically random token of at least 32 characters.
- `TOPDECK_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

Never put these secrets in frontend env files or browser bundles. Retain Vercel deployment
protection. The invite bearer token is a temporary private testing credential; it does
not implement individual invitations, revocation, or account-wide quotas.

`GET /health` returns a basic health response. `POST /simulate` requires
`Authorization: Bearer <invite token>` and a JSON body such as:

```json
{"event_id":"cardart-monthly-september-mox-diamond","swiss_rounds":4,"top_cut":16,"run_seconds":30,"simulations":2000,"seed":1}
```

Response format is newline-delimited JSON: `starting`, then existing engine snapshots,
ending in `complete` or `error`. HTTP 200 alone does not mean a simulation succeeded.
Drop settings `drop_after_round` and `drop_min_points` must be supplied together.
The stream can finish before the requested count when the time budget expires; use
`completed` to display the actual sample count. CPU work is killed on timeout/disconnect. The child inherits the parent runtime dependency
paths; helper logs use `CEDH_LOG_DIR=/tmp/cedh-simulator-logs` because deployed source is read-only.

## Validation

```bash
PYTHONPATH=packages/backend/src python -m pytest packages/backend/tests/test_simulator_api.py packages/backend/tests/test_ongoing_tournament_sim_parity.py packages/backend/tests/test_sim_engine_exact_top_cut.py
```

Before connecting PR #297, verify on the deployed runtime:

1. Authentication and invalid requests fail before simulation work starts.
2. The committed model loads and real data produces a final complete snapshot.
3. Results include every player, including events above 100 players.
4. A representative run meets latency and cost expectations.
5. A cancelled request and timeout release resources.

Local testing is not proof of Vercel compatibility or acceptable production performance.

## Trial results — 2026-09-19

Vercel Python 3.12 successfully built and ran the existing engine on a protected
preview in the same Pro team as tedh.gg, in a separate `tedh-simulator-preview` project.
Production tedh.gg was not modified. Vercel measured the full dependency bundle at
about 383 MB and applied its dependency optimization during build.

Using `cardart-monthly-september-mox-diamond` (63 players), explicit four Swiss rounds
and Top 16 for the test:

- 20 seeded simulations completed in about 61 seconds, including data preparation.
- Every player's win, top-cut, Top 16, and Top 4 probability matched the equivalent
  local seeded run exactly. This is a cross-runtime parity check, not a model accuracy claim.
- The final preview completed 705 simulations within a 10-second simulation budget,
  taking about 67 seconds overall. It returned all 63 players and a complete snapshot.
- Missing invite credentials returned HTTP 401 on the final deployment.
- 57 targeted tests passed, including lifecycle, engine parity, exact top cut, and ingestion.
  Ruff and documentation checks passed.

These measurements establish feasibility for this event only. Data preparation dominates
latency. Larger events, simultaneous callers, deployed cancellation, and account-wide cost
controls still require validation before a public release. Next work is the invite-only
web adapter in PR #297 and reducing preparation latency without changing model inputs.
