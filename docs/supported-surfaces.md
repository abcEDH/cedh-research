# Supported Surfaces

This file is the source of truth for which user-facing product surfaces are actively supported.
Planned removals should be called out explicitly, but they must not be labeled as already retired until the corresponding deletion work lands.

## Active

- `/`
- `/about`
- `/commanders`
- `/commanders/trends`
- `/limitations`
- `/midseason-invitational`
- `/regional-elo`
- `/regional-elo/player/[topdeckId]`
- `/tournament-likelihood`
- `/trap-spice`
- `/cards`
- `/turn-order`
- `/survival`
- `/methodology/data-model`
- `/methodology/elo`

## Planned Retirement

- `/cards`
- `/turn-order`
- `/survival`

These routes are still live today, but they are queued for removal under the surface-retirement workstream.

## Notes

- Active surfaces must stay in sync with onboarding docs, handover notes, and any supported-surface inventory checks.
- Planned-retirement surfaces must not be described as already deleted until the removal PR merges.
- TopDeck-powered active surfaces must show visible attribution in the UI.
