"""Hand-chosen research baseline weights; these have not been fitted or promoted.

The hybrid gives most weight to recent/lifetime usage, then smaller bonuses for
latest registration, repeating the last two registrations, and a recent decklist.
They are heuristic challenger inputs, not measured causal effects.
"""

RECENT_SHARE_WEIGHT = 0.58
LIFETIME_SHARE_WEIGHT = 0.22
LATEST_BONUS_WEIGHT = 0.10
REPEAT_BONUS_WEIGHT = 0.06
DECKLIST_SHARE_WEIGHT = 0.04
