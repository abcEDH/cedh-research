# cEDH Skill Rating

By Charles Lien and Alex Lien  
Source: https://topdeck.gg/elo/edh

## Intro

This document captures the proposed cEDH skill rating system used as the basis for our implementation.  
It adapts Elo to multiplayer (4-player) cEDH games.

## Background

cEDH has five outcomes in a pod:

1. Player 1 wins
2. Player 2 wins
3. Player 3 wins
4. Player 4 wins
5. Draw

Classic Elo is designed for 1v1 zero-sum games. This model generalizes expected value to multiplayer.

## Core assumptions

- Zero-sum: total game value is constant across outcomes.
- Symmetry: seat identity does not change value.
- Value range: each player's game value `V` is in `[0, 1]`.
- Draw value: for a 4-player draw, each player gets `1/4`.

## Equity model

Each player has equity `E_i`, and expected value is:

`EV(V_i) = E_i / (E_1 + E_2 + E_3 + E_4)`

This is a softmax-style model (logit -> exponent -> normalized probability).

## Proposed 4-player Elo

- Initial rating: `1500`
- Equity for rating `R`: `2^(R/200)`
- Update rule:

`R'_A = R_A + K * (S_A - E_A)`

Where:

- `K` is learning rate (`48` in our current implementation)
- `S_A` is actual result (`1` win, `0` loss, `1/n` draw in n-player pod)
- `E_A` is expected result:

`E_A = 2^(R_A/200) / (2^(R_A/200) + 2^(R_B/200) + 2^(R_C/200) + 2^(R_D/200))`

## Implementation process

1. Build chronologically ordered games.
2. Initialize all unseen players at `1500`.
3. For each game, for each player:
   - Compute equity.
   - Compute expected score.
   - Compute actual score.
   - Apply Elo update.

## Design notes

### Draws

- Draws are common in cEDH tournament play.
- Model choice: treat draw as fractional win (`1/n`) to preserve zero-sum consistency.

### Non-4-player games

- Keep them in the dataset.
- Draw value scales by player count (`1/n`).

### Rating decay

Not currently applied to base rating updates.  
Practical visibility rule can be used instead (e.g., minimum recent games to appear on leaderboard).

### Cheaters

Suggested policy: keep games in ratings for stability, but remove cheaters from public leaderboard display.

## Alternatives considered

- Equity model with different underlying distributions (log-normal, log-uniform)
- Winner-takes-all distribution model
- Explicit decay models toward baseline rating

## Current product status

Our code follows the equity-based Elo variant above and currently uses:

- `Initial rating = 1500`
- `K = 48`
- `Equity = 2^(R/200)`
- `Draw = 1/n`
- A single global rating computed from all included games

## State assignment

State leaderboards are derived from the global rating, not from separate state-local Elo pools.

For each player and state, we track:

- games in the last 30 days
- games in the last 90 days
- games in the last 365 days
- lifetime games in that state
- latest game date in that state

We then compute a weighted activity score that emphasizes recent play and uses lifetime volume as a
light stabilizer. A player is assigned to the state with the highest activity score.
