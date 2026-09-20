# 0024 - Shared internal Elo parameters

## Status
Accepted

## Context

The simulator and Elo maintenance had separate copies of the Elo scale, seat adjustments, and learning rates. Updating the published Elo model left simulation predictions and reconstructed live ratings using earlier parameters. A manually versioned prepared-state cache could also retain old calculations after a weight change.

## Decision

- Keep current internal Elo parameters in `packages/backend/src/internal_elo.py`.
- Global rating rebuild, all-games recompute, simulation inference, and live replay consume that module. Swiss and top cut use the corresponding stage offsets.
- Use the shared rating-equity helper for the base and divisor rather than embedding the formula's parameters in consumers.
- Include a fingerprint of the actual parameters in prepared-state cache keys. Invalidation must work even if the model-version string is unchanged.
- Maintain regression tests that change shared values and verify propagation across consumers and cache keys.
- Displayed TopDeck Elo remains a separate source. Publishing reconstructed historical Elo remains a manual maintenance operation under ADR 0008.

## Consequences

Future parameter updates have one edit location. Updating weights no longer requires coordinating numeric copies or manually bumping simulation-cache versions. Consumers still need to run/deploy the updated code; changing the source does not automatically rewrite database ratings.

This decision unifies parameters. It does not make legacy outcome normalization, historical draw handling, or reporting identical across every maintenance utility.

### Cross-Repo Impact

`cedh-research` only.

## Sources

- User request: future Elo updates must change both Elo calculations and the simulator.
- `internal_elo.py` and `test_internal_elo_shared.py`.
- [Simulation Elo methodology](../methodology/simulation-elo.md).
