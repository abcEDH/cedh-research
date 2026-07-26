"""Self-healing partner-order dedup applied at ingestion write time.

Issue #260: partner-commander pairs were splitting into separate
``commanders`` rows depending on decklist name order ("A, B" vs "B, A").
``commander_normalization.py`` already computes one canonical order for any
two-card pair (via ``normalize_partner_order`` / ``sanitize_commander_payload``),
and ``ingest.py`` has always upserted new commander rows under that canonical
name -- so brand-new pairs written from scratch already land in one row.

The gap was rows that were written under a *non-canonical* order before this
pair's canonical order was known (e.g. before it was added to
``legal_commander_pairings.json`` or ``PARTNER_ORDER_OVERRIDES``, or before
``sanitize_commander_payload`` existed at all). Ingesting a new tournament for
that same pair then creates a second row under the now-canonical name,
leaving the old row's tournament history stranded under the old name --
exactly the "still splitting" symptom the issue reports. Previously the only
fix was to re-run ``sweep_partner_commander_order.py`` by hand.

``resolve_partner_order_conflicts`` closes that gap by running automatically
as part of every ingestion, right before commanders are upserted: it looks
for any existing row(s) under the *other* name order for a pair about to be
written, and heals them in place --

- if no row uses the canonical order yet, the stray row is renamed in place
  (same id, so every FK referencing it stays intact -- no repoint needed);
- if a canonical row already exists too (a true historic duplicate), the
  stray row's ``tournament_entries``/``commander_matchups`` foreign keys are
  repointed onto the canonical row and the stray row is deleted -- the same
  merge mechanics ``sweep_partner_commander_order.py`` uses for its one-off
  backfill, just applied continuously instead of on a manual re-run.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _merge_duplicate_commander(client: Any, canonical_id: str, duplicate_id: str) -> None:
    """Repoint every FK off ``duplicate_id`` onto ``canonical_id``, then delete it.

    ``commander_matchups`` has foreign keys from both ``commander_id`` and
    ``opponent_commander_id`` to ``commanders`` (see
    ``20260110000001_initial_schema.sql``), so both columns must be repointed
    -- alongside ``tournament_entries.commander_id`` -- before the duplicate
    row can be deleted, or Postgres rejects the delete with an FK violation.
    Filtering by ``eq.<duplicate_id>`` makes every repoint idempotent, so a
    retry after a partial failure is safe.
    """
    client.update("tournament_entries", {"commander_id": canonical_id}, {"commander_id": f"eq.{duplicate_id}"})
    client.update("commander_matchups", {"commander_id": canonical_id}, {"commander_id": f"eq.{duplicate_id}"})
    client.update(
        "commander_matchups",
        {"opponent_commander_id": canonical_id},
        {"opponent_commander_id": f"eq.{duplicate_id}"},
    )
    client.delete("commanders", {"id": f"eq.{duplicate_id}"})
    logger.info("commander_dedup: merged duplicate id=%s into canonical id=%s", duplicate_id, canonical_id)


def resolve_partner_order_conflicts(
    client: Any,
    commander_payloads: dict[str, list[str]],
    *,
    commander_limit: int = 5000,
) -> None:
    """Heal any pre-existing alt-order duplicate rows before the normal upsert.

    ``commander_payloads`` maps each canonical commander name about to be
    written to its canonical ``commander_names`` list, i.e. the output of
    ``sanitize_commander_payload`` for every commander in the current batch.
    Only two-card partner pairs are relevant here -- single commanders have
    no alternate order to collide with.
    """
    pair_targets: dict[tuple[str, str], tuple[str, list[str]]] = {}
    for canonical_name, names in commander_payloads.items():
        if len(names) != 2:
            continue
        pair_targets[tuple(sorted(names))] = (canonical_name, names)

    if not pair_targets:
        return

    existing_rows = client.select(
        "commanders",
        {"select": "id,name,commander_names", "limit": commander_limit},
    )

    rows_by_pair_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in existing_rows:
        row_names = row.get("commander_names") or []
        if len(row_names) != 2:
            continue
        rows_by_pair_key.setdefault(tuple(sorted(row_names)), []).append(row)

    for pair_key, (canonical_name, canonical_names) in pair_targets.items():
        rows = rows_by_pair_key.get(pair_key)
        if not rows:
            continue  # Nothing to heal; the normal upsert will insert it fresh.

        canonical_row = next((row for row in rows if row.get("name") == canonical_name), None)
        stray_rows = [row for row in rows if row is not canonical_row]

        if canonical_row is None:
            # Repurpose the first stray row in place: same id, so every FK
            # already pointing at it (tournament_entries, commander_matchups)
            # stays valid without any repoint.
            canonical_row = stray_rows.pop(0)
            client.update(
                "commanders",
                {"name": canonical_name, "commander_names": canonical_names},
                {"id": f"eq.{canonical_row['id']}"},
            )
            logger.info(
                "commander_dedup: renamed legacy partner-order duplicate %r -> %r (id=%s)",
                canonical_row.get("name"),
                canonical_name,
                canonical_row["id"],
            )

        for stray_row in stray_rows:
            _merge_duplicate_commander(client, canonical_row["id"], stray_row["id"])
