#!/usr/bin/env python3
"""Train the candidate-player decisive winner model artifact."""

from __future__ import annotations

import argparse
import json
import pickle
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evaluate_candidate_winner_model import (
    CANDIDATE_FEATURES,
    build_candidate_examples,
    fit_candidate_model,
)
from evaluate_pod_outcome_vs_draw_elo import is_valid_outcome_row, load_cached_rows, row_date, row_value
from train_draw_model import DEFAULT_CACHE_PATH


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports" / "winner-model" / "v1"
DEFAULT_PARTICIPANT_CACHE_PATH = DATA_DIR / "candidate_winner_eval_participants.pkl"
DEFAULT_ARTIFACT_PATH = REPORTS_DIR / "cedh_candidate_winner_model_artifact_v1.pkl"
DEFAULT_REPORT_PATH = REPORTS_DIR / "cedh_candidate_winner_model_report_v1.json"


def load_participant_payload(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    if isinstance(payload, dict) and "payload" in payload:
        return payload["payload"]
    if isinstance(payload, dict):
        return payload
    raise TypeError(f"Unsupported participant cache payload: {type(payload)!r}")


def maybe_limit_newest_rows(rows: list[Any], limit: int | None) -> list[Any]:
    if not limit or limit <= 0 or len(rows) <= limit:
        return rows
    return sorted(rows, key=lambda row: (row_date(row), str(row_value(row, "game_id", ""))))[-limit:]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH))
    parser.add_argument("--participant-cache-path", default=str(DEFAULT_PARTICIPANT_CACHE_PATH))
    parser.add_argument("--artifact-path", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--limit-rows", type=int)
    parser.add_argument("--blend-weight", type=float, default=1.0)
    args = parser.parse_args()

    started = time.perf_counter()
    rows = [
        row
        for row in load_cached_rows(Path(args.cache_path))
        if is_valid_outcome_row(row) and row_value(row, "tournament_id")
    ]
    rows = maybe_limit_newest_rows(rows, args.limit_rows)
    participant_payload = load_participant_payload(Path(args.participant_cache_path))
    examples = build_candidate_examples(rows, participant_payload)
    if not examples:
        raise RuntimeError("No candidate winner examples were built")

    model = fit_candidate_model(examples)
    blend_weight = max(0.0, min(1.0, float(args.blend_weight)))
    artifact = {
        "target": "candidate_winner",
        "artifact_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "hist_gradient_boosting",
        "features": list(CANDIDATE_FEATURES),
        "model": model,
        "blend_weight": blend_weight,
        "classes": [int(value) for value in model.classes_],
    }

    artifact_path = Path(args.artifact_path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_path.open("wb") as handle:
        pickle.dump(artifact, handle, protocol=pickle.HIGHEST_PROTOCOL)

    label_counts = Counter(example.label for example in examples)
    tournaments = {str(row_value(row, "tournament_id", "") or "") for row in rows}
    report = {
        "target": "candidate_winner",
        "artifact_version": 1,
        "generated_at": artifact["generated_at"],
        "runtime_seconds": time.perf_counter() - started,
        "artifact_path": str(artifact_path),
        "cache_path": str(Path(args.cache_path)),
        "participant_cache_path": str(Path(args.participant_cache_path)),
        "rows": {
            "pods": len(rows),
            "candidate_examples": len(examples),
            "tournaments": len(tournaments),
        },
        "date_range": {
            "start": min(row_date(row) for row in rows).isoformat() if rows else None,
            "end": max(row_date(row) for row in rows).isoformat() if rows else None,
        },
        "features": list(CANDIDATE_FEATURES),
        "blend_weight": blend_weight,
        "classes": [int(value) for value in model.classes_],
        "label_counts": {str(label): count for label, count in sorted(label_counts.items())},
    }
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
