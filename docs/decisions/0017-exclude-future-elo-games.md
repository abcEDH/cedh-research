# 0017 — Exclude future games from Elo

## Status

Accepted

## Context

A test tournament dated October 2030 entered the Elo event log. Incremental maintenance used that event as its latest processed date and skipped missing 2026 games while reporting success. Date-only eligibility checks also admitted games starting later on the current day.

## Decision

- A tournament start timestamp must be at or before the current UTC instant to contribute to Elo, regardless of dataset tier. Future tournaments remain in the raw ingestion tables.
- Enforce this at both Elo result views, on event writes with a database constraint, and in Python before scoring cached or directly fetched inputs.
- Bound the incremental watermark to the current instant and refuse future snapshot cutoffs. Reject an entire pod if any participant is future-dated.
- Existing future events require chronological recovery from uncontaminated history. Filtering the watermark alone cannot recover games already skipped or undo corrupted ratings.
- Use the existing canonical rebuild eligibility and rating formulas for recovery. Prepare and validate outputs before atomically publishing all derived tables. Preserve displayed TopDeck Elo as a separate value.

## Consequences

Maintenance cannot advance its restart point into the future. Raw bad dates remain available for investigation and later correction. The event constraint is initially installed `NOT VALID` to permit recovery of existing invalid records; recovery must validate it after removing those records. Completeness must be checked against eligible game IDs, not inferred from a successful job or the largest date alone.

### Cross-Repo Impact

`cedh-research` only. No change to displayed TopDeck Elo or tournament ingestion ownership.

## Sources

- [Maintenance run 34937202746](https://github.com/abcEDH/cedh-research/actions/runs/34937202746), which selected an October 2030 watermark in September 2026.
- Migration `20260915000000_exclude_future_elo_games.sql`.
