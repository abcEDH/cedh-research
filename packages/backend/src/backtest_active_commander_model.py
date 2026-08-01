#!/usr/bin/env python3
"""Backtest active-commander prediction models.

The target is the next known commander a player registers with. For each
historical entry, this script hides that entry and predicts from only prior
known commander history for the same TopDeck id.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict
from datetime import date, datetime, time, timezone
from typing import Any

from dateutil import parser as date_parser

from ingest import SUPABASE_REST_BASE, SupabaseClient, load_local_env
from rebuild_player_commander_profiles import (
    LATEST_COMMANDER_BLEND_WEIGHT,
    build_profile_rows,
    calculate_recency_weight,
    fetch_usage_rows_via_db,
    fetch_usage_rows_via_rest,
    is_known_commander,
    latest_usage_row,
    normalize_usage_rows,
    select_commander_forecast_rows,
)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover
    psycopg2 = None

UTC = timezone.utc
HYBRID_HALF_LIFE_DAYS = 45
EPSILON = 1e-9


def parse_start_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    else:
        parsed = date_parser.parse(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def commander_from_row(row: dict[str, Any]) -> str | None:
    commander = row.get("commander_name")
    return commander if is_known_commander(commander) else None


def normalize_usage_start_dates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        start_date = row.get("start_date")
        if isinstance(start_date, datetime):
            normalized.append({**row, "start_date": start_date.isoformat()})
        elif isinstance(start_date, date):
            normalized.append({**row, "start_date": datetime.combine(start_date, time.min).isoformat()})
        else:
            normalized.append(row)
    return normalized


def prediction_timestamp_ms(reference_date: date) -> int:
    return int(datetime.combine(reference_date, datetime.min.time(), tzinfo=UTC).timestamp() * 1000)


def recency_weight_for_row(row: dict[str, Any], reference_timestamp_ms: int, half_life_days: int) -> float:
    start_date = row.get("start_date")
    if not start_date:
        return 0.0
    parsed = parse_start_datetime(start_date)
    if parsed is None:
        return 0.0
    event_timestamp_ms = int(parsed.timestamp() * 1000)
    age_in_days = max(0.0, (reference_timestamp_ms - event_timestamp_ms) / (1000 * 60 * 60 * 24))
    return 0.5 ** (age_in_days / half_life_days)


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    positive = {key: max(0.0, value) for key, value in scores.items() if value > 0}
    total = sum(positive.values())
    if total <= 0:
        return {}
    return {key: value / total for key, value in positive.items()}


def latest_known_distribution(history_rows: list[dict[str, Any]]) -> dict[str, float]:
    latest = latest_usage_row(history_rows)
    commander = commander_from_row(latest or {})
    return {commander: 1.0} if commander else {}


def most_played_distribution(history_rows: list[dict[str, Any]], _reference_date: date | None = None) -> dict[str, float]:
    counts: dict[str, float] = defaultdict(float)
    for row in history_rows:
        commander = commander_from_row(row)
        if commander:
            counts[commander] += 1.0
    return normalize_scores(counts)


def current_profile_distribution(history_rows: list[dict[str, Any]], reference_date: date) -> dict[str, float]:
    if not history_rows:
        return {}
    rows_by_topdeck_id = defaultdict(list)
    for row in history_rows:
        rows_by_topdeck_id[row["topdeck_id"]].append(row)
    selected = select_commander_forecast_rows(rows_by_topdeck_id, reference_date)
    topdeck_id = history_rows[0]["topdeck_id"]
    selected_rows = selected.get(topdeck_id, [])
    reference_timestamp_ms = prediction_timestamp_ms(reference_date)
    scores: dict[str, float] = defaultdict(float)
    for row in selected_rows:
        commander = commander_from_row(row)
        if not commander:
            continue
        start_date = row.get("start_date")
        event_timestamp_ms = 0
        if start_date:
            event_timestamp_ms = int(parse_start_datetime(start_date).timestamp() * 1000)  # type: ignore[union-attr]
        scores[commander] += calculate_recency_weight(event_timestamp_ms, reference_timestamp_ms)
    return normalize_scores(scores)


def hybrid_distribution(history_rows: list[dict[str, Any]], reference_date: date) -> dict[str, float]:
    if not history_rows:
        return {}

    rows_by_topdeck_id = defaultdict(list)
    for row in history_rows:
        rows_by_topdeck_id[row["topdeck_id"]].append(row)
    topdeck_id = history_rows[0]["topdeck_id"]
    selected_rows = select_commander_forecast_rows(rows_by_topdeck_id, reference_date).get(topdeck_id, [])
    if not selected_rows:
        selected_rows = history_rows

    reference_timestamp_ms = prediction_timestamp_ms(reference_date)
    recent_scores: dict[str, float] = defaultdict(float)
    lifetime_counts: dict[str, int] = defaultdict(int)
    selected_counts: dict[str, int] = defaultdict(int)
    decklist_counts: dict[str, int] = defaultdict(int)

    for row in history_rows:
        commander = commander_from_row(row)
        if commander:
            lifetime_counts[commander] += 1

    for row in selected_rows:
        commander = commander_from_row(row)
        if not commander:
            continue
        selected_counts[commander] += 1
        if row.get("decklist_url") or row.get("topdeck_decklist_url"):
            decklist_counts[commander] += 1
        recent_scores[commander] += recency_weight_for_row(
            row,
            reference_timestamp_ms,
            HYBRID_HALF_LIFE_DAYS,
        )

    if not recent_scores:
        return {}

    recent_share = normalize_scores(recent_scores)
    lifetime_share = normalize_scores({key: float(value) for key, value in lifetime_counts.items()})
    decklist_share = normalize_scores({key: float(value) for key, value in decklist_counts.items()})

    latest_commander = commander_from_row(latest_usage_row(history_rows) or {})
    sorted_history = sorted(history_rows, key=lambda row: row.get("start_date") or "", reverse=True)
    latest_two = [commander_from_row(row) for row in sorted_history[:2]]
    repeat_latest = latest_two[0] if len(latest_two) >= 2 and latest_two[0] and latest_two[0] == latest_two[1] else None

    commanders = set(recent_share) | set(lifetime_share) | set(decklist_share)
    scores: dict[str, float] = {}
    for commander in commanders:
        latest_bonus = 1.0 if commander == latest_commander else 0.0
        repeat_bonus = 1.0 if commander == repeat_latest else 0.0
        scores[commander] = (
            0.58 * recent_share.get(commander, 0.0)
            + 0.22 * lifetime_share.get(commander, 0.0)
            + 0.10 * latest_bonus
            + 0.06 * repeat_bonus
            + 0.04 * decklist_share.get(commander, 0.0)
        )
    return normalize_scores(scores)


def latest_blend_distribution(
    history_rows: list[dict[str, Any]],
    reference_date: date,
    *,
    latest_weight: float,
) -> dict[str, float]:
    current = current_profile_distribution(history_rows, reference_date)
    latest = latest_known_distribution(history_rows)
    commanders = set(current) | set(latest)
    return normalize_scores(
        {
            commander: (
                (1 - latest_weight) * current.get(commander, 0.0)
                + latest_weight * latest.get(commander, 0.0)
            )
            for commander in commanders
        }
    )


def production_distribution(history_rows: list[dict[str, Any]], reference_date: date) -> dict[str, float]:
    return latest_blend_distribution(
        history_rows,
        reference_date,
        latest_weight=LATEST_COMMANDER_BLEND_WEIGHT,
    )


def sorted_predictions(distribution: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(distribution.items(), key=lambda item: (-item[1], item[0]))


def evaluate_prediction(distribution: dict[str, float], actual: str) -> dict[str, Any]:
    predictions = sorted_predictions(distribution)
    predicted = predictions[0][0] if predictions else None
    top3 = {commander for commander, _ in predictions[:3]}
    probability = max(EPSILON, distribution.get(actual, 0.0))
    return {
        "predicted": predicted,
        "top1": predicted == actual,
        "top3": actual in top3,
        "log_loss": -math.log(probability),
        "actual_probability": probability,
    }


def build_backtest_examples(
    usage_rows: list[dict[str, Any]],
    *,
    min_history: int,
    since: date | None = None,
    limit_targets: int | None = None,
) -> list[dict[str, Any]]:
    rows_by_topdeck_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in usage_rows:
        if row.get("topdeck_id") and row.get("start_date") and commander_from_row(row):
            rows_by_topdeck_id[row["topdeck_id"]].append(row)

    examples: list[dict[str, Any]] = []
    for topdeck_id, player_rows in rows_by_topdeck_id.items():
        player_rows.sort(key=lambda row: (row.get("start_date") or "", row.get("tournament_id") or ""))
        for index, row in enumerate(player_rows):
            target_start = parse_start_datetime(row.get("start_date"))
            actual = commander_from_row(row)
            if target_start is None or actual is None:
                continue
            if since and target_start.date() < since:
                continue
            history_rows = [
                history_row
                for history_row in player_rows[:index]
                if (history_row.get("start_date") or "") < (row.get("start_date") or "")
            ]
            if len(history_rows) < min_history:
                continue
            examples.append(
                {
                    "topdeck_id": topdeck_id,
                    "player_name": row.get("player_name") or "Unknown",
                    "target_date": target_start.date(),
                    "actual": actual,
                    "history_rows": history_rows,
                    "target_row": row,
                }
            )

    examples.sort(key=lambda example: (example["target_date"], example["topdeck_id"]))
    if limit_targets:
        examples = examples[-limit_targets:]
    return examples


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    if total == 0:
        return {"targets": 0, "top1_accuracy": 0.0, "top3_accuracy": 0.0, "log_loss": 0.0}
    return {
        "targets": total,
        "top1_accuracy": sum(1 for row in results if row["top1"]) / total,
        "top3_accuracy": sum(1 for row in results if row["top3"]) / total,
        "log_loss": sum(float(row["log_loss"]) for row in results) / total,
    }


def model_predictions_for_examples(
    examples: list[dict[str, Any]],
    models: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    results_by_model: dict[str, list[dict[str, Any]]] = {name: [] for name in models}
    for example in examples:
        reference_date = example["target_date"]
        actual = example["actual"]
        history_rows = example["history_rows"]
        for model_name, predict in models.items():
            distribution = predict(history_rows, reference_date)
            evaluated = evaluate_prediction(distribution, actual)
            results_by_model[model_name].append({**evaluated, "example": example})
    return results_by_model


def run_backtest(examples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    models = {
        "current": current_profile_distribution,
        "production": production_distribution,
        "last_played": lambda history, ref_date: latest_known_distribution(history),
        "most_played": most_played_distribution,
        "hybrid": hybrid_distribution,
    }
    results_by_model = model_predictions_for_examples(examples, models)
    return {name: summarize_results(results) for name, results in results_by_model.items()}


def production_matches_rebuild_top_choice(history_rows: list[dict[str, Any]], reference_date: date) -> bool:
    profile_rows = build_profile_rows(history_rows, reference_date)
    profile_active = profile_rows[0]["active_commander"] if profile_rows else None
    production_predictions = sorted_predictions(production_distribution(history_rows, reference_date))
    production_active = production_predictions[0][0] if production_predictions else None
    return profile_active == production_active


def latest_weight_sweep(
    examples: list[dict[str, Any]],
    weights: list[float],
) -> dict[str, dict[str, Any]]:
    models = {
        f"latest_weight_{weight:.2f}": (
            lambda history, ref_date, blend_weight=weight: latest_blend_distribution(
                history,
                ref_date,
                latest_weight=blend_weight,
            )
        )
        for weight in weights
    }
    results_by_model = model_predictions_for_examples(examples, models)
    return {name: summarize_results(results) for name, results in results_by_model.items()}


def history_count_bucket(example: dict[str, Any]) -> str:
    count = len(example["history_rows"])
    if count <= 2:
        return "history_count=2"
    if count <= 5:
        return "history_count=3-5"
    if count <= 10:
        return "history_count=6-10"
    return "history_count=11+"


def latest_age_bucket(example: dict[str, Any]) -> str:
    latest = latest_usage_row(example["history_rows"])
    latest_start = parse_start_datetime((latest or {}).get("start_date"))
    target_start = datetime.combine(example["target_date"], time.min, tzinfo=UTC)
    if latest_start is None:
        return "latest_age=unknown"
    days = max(0, (target_start - latest_start).days)
    if days <= 30:
        return "latest_age<=30d"
    if days <= 90:
        return "latest_age=31-90d"
    if days <= 180:
        return "latest_age=91-180d"
    return "latest_age=181d+"


def run_bucket_backtest(
    examples: list[dict[str, Any]],
    predict=production_distribution,
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for example in examples:
        distribution = predict(example["history_rows"], example["target_date"])
        evaluated = evaluate_prediction(distribution, example["actual"])
        buckets[history_count_bucket(example)].append(evaluated)
        buckets[latest_age_bucket(example)].append(evaluated)
    return {name: summarize_results(results) for name, results in sorted(buckets.items())}


def fetch_usage_rows_for_target_window_via_db(
    db_url: str,
    *,
    since: date,
    limit_targets: int | None = None,
) -> list[dict[str, Any]]:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required for direct database reads")

    limit_clause = "LIMIT %(limit_targets)s" if limit_targets else ""
    sql = f"""
        WITH target_rows AS (
            SELECT te.player_id, t.start_date, te.id
            FROM tournament_entries te
            JOIN players p ON p.id = te.player_id
            JOIN commanders c ON c.id = te.commander_id
            JOIN tournaments t ON t.id = te.tournament_id
            WHERE p.topdeck_id IS NOT NULL
              AND c.name IS NOT NULL
              AND lower(btrim(c.name)) <> 'unknown commander'
              AND t.start_date::date >= %(since)s
            ORDER BY t.start_date DESC, te.id DESC
            {limit_clause}
        ),
        target_players AS (
            SELECT DISTINCT player_id FROM target_rows
        )
        SELECT
            te.player_id,
            te.decklist_url,
            p.topdeck_id,
            p.name AS player_name,
            c.name AS commander_name,
            t.id AS tournament_id,
            t.name AS tournament_name,
            t.start_date,
            t.topdeck_tid
        FROM tournament_entries te
        JOIN target_players tp ON tp.player_id = te.player_id
        JOIN players p ON p.id = te.player_id
        JOIN commanders c ON c.id = te.commander_id
        JOIN tournaments t ON t.id = te.tournament_id
        WHERE p.topdeck_id IS NOT NULL
          AND c.name IS NOT NULL
        ORDER BY te.player_id ASC, t.start_date ASC, te.id ASC
    """
    params: dict[str, Any] = {"since": since.isoformat()}
    if limit_targets:
        params["limit_targets"] = int(limit_targets)

    with psycopg2.connect(db_url, connect_timeout=15) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]


def load_usage_rows(since: date | None = None, limit_targets: int | None = None) -> list[dict[str, Any]]:
    load_local_env()
    supabase_url = os.environ.get("SUPABASE_URL", SUPABASE_REST_BASE)
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_key:
        raise SystemExit("SUPABASE_SERVICE_KEY is required")
    db_url = os.environ.get("SUPABASE_DB_URL")
    if db_url:
        try:
            if since:
                return normalize_usage_start_dates(
                    normalize_usage_rows(
                        fetch_usage_rows_for_target_window_via_db(
                            db_url,
                            since=since,
                            limit_targets=limit_targets,
                        )
                    )
                )
            return normalize_usage_start_dates(normalize_usage_rows(fetch_usage_rows_via_db(db_url)))
        except Exception as exc:
            print(f"Direct database read failed, falling back to REST: {exc}")
    client = SupabaseClient(supabase_url, supabase_key)
    return normalize_usage_start_dates(normalize_usage_rows(fetch_usage_rows_via_rest(client)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest active commander prediction models")
    parser.add_argument("--min-history", type=int, default=2)
    parser.add_argument("--since", type=str, help="Only test targets on/after YYYY-MM-DD")
    parser.add_argument("--limit-targets", type=int, help="Use only the most recent N targets")
    parser.add_argument(
        "--latest-weight-sweep",
        action="store_true",
        help="Also test latest-commander blend weights from 0.00 through 0.50",
    )
    parser.add_argument(
        "--bucket-report",
        action="store_true",
        help="Also print production metrics by history count and latest-history age buckets",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    since = date_parser.parse(args.since).date() if args.since else None
    usage_rows = load_usage_rows(since=since, limit_targets=args.limit_targets)
    examples = build_backtest_examples(
        usage_rows,
        min_history=args.min_history,
        since=since,
        limit_targets=args.limit_targets,
    )
    summary = run_backtest(examples)
    output: dict[str, Any] = {"summary": summary}
    if args.latest_weight_sweep:
        output["latest_weight_sweep"] = latest_weight_sweep(
            examples,
            [round(weight / 100, 2) for weight in range(0, 51, 5)],
        )
    if args.bucket_report:
        output["bucket_report"] = run_bucket_backtest(examples)

    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
        return

    print(f"Backtested {len(examples)} known next-commander targets")
    print("model     targets  top1     top3     log_loss")
    for model_name, result in sorted(summary.items()):
        print(
            f"{model_name:<9} {result['targets']:>7}  "
            f"{result['top1_accuracy']:.3f}  {result['top3_accuracy']:.3f}  {result['log_loss']:.3f}"
        )
    if args.latest_weight_sweep:
        print()
        print("latest weight sweep")
        print("weight    targets  top1     top3     log_loss")
        for model_name, result in sorted(output["latest_weight_sweep"].items()):
            weight = model_name.removeprefix("latest_weight_")
            print(
                f"{weight:>6}  {result['targets']:>7}  "
                f"{result['top1_accuracy']:.3f}  {result['top3_accuracy']:.3f}  {result['log_loss']:.3f}"
            )
    if args.bucket_report:
        print()
        print("production bucket report")
        print("bucket               targets  top1     top3     log_loss")
        for bucket_name, result in output["bucket_report"].items():
            print(
                f"{bucket_name:<20} {result['targets']:>7}  "
                f"{result['top1_accuracy']:.3f}  {result['top3_accuracy']:.3f}  {result['log_loss']:.3f}"
            )


if __name__ == "__main__":
    main()
