"""Backend maintenance validations used by GitHub Actions and local runs."""

from __future__ import annotations

import argparse
import os
import time
from typing import Any

import requests


RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
PAGE_SIZE = 100
STATE_SAMPLE_SIZE = 25


VIEW_SPECS: list[tuple[str, int]] = [
    ("commander_stats", 10),
    ("seat_position_stats", 4),
    ("commander_seat_stats", 10),
    ("card_frequencies_global", 100),
    ("card_frequencies_by_commander", 100),
    ("trap_cards_report", 1),
    ("spice_cards_report", 1),
    ("seat_survival_by_commander", 10),
    ("seat_survival_by_round", 4),
    ("commander_survival_curve", 10),
    ("commander_tournament_depth", 10),
    ("player_survival_stats", 10),
    ("commander_meta_monthly", 5),
    ("commander_momentum", 1),
    ("commander_first_appearances", 10),
    ("survival_summary", 10),
    ("regional_elo_player_stats", 10),
    ("regional_elo_regions", 2),
    ("regional_elo_game_event_log", 100),
]

RPC_SPECS: list[tuple[str, dict[str, Any], bool]] = [
    ("get_notable_players_for_commander", {"p_commander_id": "00000000-0000-0000-0000-000000000000"}, False),
    ("get_commander_matchups", {"p_commander_id": "00000000-0000-0000-0000-000000000000"}, False),
    ("get_commanders_for_card", {"p_card_name": "Sol Ring"}, True),
]

TABLE_SPECS: list[tuple[str, int]] = [
    ("tournaments", 50),
    ("commanders", 100),
    ("tournament_entries", 3000),
    ("games", 5000),
    ("game_participants", 15000),
    ("players", 2000),
    ("regional_elo_state_activity", 10),
    ("regional_elo_game_events", 100),
]


def get_supabase_env() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY.")
    return url, key


def supabase_headers(*, count_prefer: str | None = None) -> dict[str, str]:
    _, key = get_supabase_env()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if count_prefer:
        headers["Prefer"] = count_prefer
    return headers


def request_with_retry(method: str, url: str, **kwargs: Any) -> requests.Response:
    last_response: requests.Response | None = None
    for attempt in range(RETRY_ATTEMPTS):
        response = requests.request(method, url, **kwargs)
        last_response = response
        if response.status_code < 500:
            return response
        if attempt < RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_BACKOFF_SECONDS**attempt)
    assert last_response is not None
    return last_response


def response_failure(response: requests.Response) -> str:
    body = response.text[:500] if response.text else "<empty body>"
    return f"HTTP {response.status_code}: {body}"


def validate_views() -> None:
    supabase_url, _ = get_supabase_env()
    headers = supabase_headers()
    failed: list[tuple[str, str]] = []
    passed: list[str] = []

    print("=" * 60)
    print("VALIDATING VIEWS")
    print("=" * 60)

    for view_name, min_rows in VIEW_SPECS:
        try:
            url = f"{supabase_url}/rest/v1/{view_name}?select=*&limit=100"
            resp = request_with_retry("GET", url, headers=headers, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                row_count = len(data)
                if row_count >= min_rows:
                    print(f"✓ {view_name}: {row_count} rows (expected >= {min_rows})")
                    passed.append(view_name)
                else:
                    print(f"✗ {view_name}: {row_count} rows (expected >= {min_rows})")
                    failed.append((view_name, f"Only {row_count} rows"))
            else:
                reason = response_failure(resp)
                print(f"✗ {view_name}: {reason}")
                failed.append((view_name, reason))
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            print(f"✗ {view_name}: {exc}")
            failed.append((view_name, str(exc)))

    print()
    print("=" * 60)
    print("VALIDATING RPC FUNCTIONS")
    print("=" * 60)

    for func_name, params, expect_data in RPC_SPECS:
        try:
            url = f"{supabase_url}/rest/v1/rpc/{func_name}"
            resp = request_with_retry("POST", url, headers=headers, json=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                row_count = len(data) if isinstance(data, list) else 1
                if expect_data and row_count == 0:
                    print(f"✗ {func_name}: Expected data but got empty result")
                    failed.append((func_name, "Expected data but got empty"))
                else:
                    print(f"✓ {func_name}: {row_count} rows returned")
                    passed.append(func_name)
            else:
                reason = response_failure(resp)
                print(f"✗ {func_name}: {reason}")
                failed.append((func_name, reason))
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            print(f"✗ {func_name}: {exc}")
            failed.append((func_name, str(exc)))

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailed items:")
        for item, reason in failed:
            print(f"  - {item}: {reason}")
        raise SystemExit(1)

    print("\nAll validations passed!")


def get_table_count(supabase_url: str, headers: dict[str, str], table_name: str) -> tuple[int, str]:
    methods = [
        ("HEAD", "count=exact", f"{supabase_url}/rest/v1/{table_name}?select=count", None),
        ("GET", "count=exact", f"{supabase_url}/rest/v1/{table_name}?select=id", {"limit": 1}),
        ("GET", "count=planned", f"{supabase_url}/rest/v1/{table_name}?select=id", {"limit": 1}),
        ("GET", "count=estimated", f"{supabase_url}/rest/v1/{table_name}?select=id", {"limit": 1}),
    ]

    errors: list[str] = []
    for method, prefer, url, params in methods:
        try:
            attempt_headers = headers.copy()
            attempt_headers["Prefer"] = prefer
            resp = requests.request(method, url, headers=attempt_headers, params=params, timeout=30)
            if resp.status_code not in (200, 206):
                errors.append(f"{method} {prefer}: HTTP {resp.status_code}")
                continue

            content_range = resp.headers.get("content-range", "0-0/0")
            count = int(content_range.split("/")[1])
            return count, f"{method} {prefer}"
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            errors.append(f"{method} {prefer}: {exc}")

    raise RuntimeError("; ".join(errors))


def validate_data_integrity() -> None:
    supabase_url, _ = get_supabase_env()
    headers = supabase_headers(count_prefer="count=exact")
    failed: list[tuple[str, str]] = []

    print("=" * 60)
    print("DATA INTEGRITY CHECK")
    print("=" * 60)

    for table_name, min_count in TABLE_SPECS:
        try:
            count, strategy = get_table_count(supabase_url, headers, table_name)
            status = "✓" if count >= min_count else "✗"
            print(
                f"{status} {table_name}: {count:,} rows "
                f"(expected >= {min_count:,}; via {strategy})"
            )
            if count < min_count:
                failed.append((table_name, f"{count} < {min_count} via {strategy}"))
        except Exception as exc:  # pragma: no cover - CI diagnostic path
            print(f"✗ {table_name}: {exc}")
            failed.append((table_name, str(exc)))

    print()
    if failed:
        print(f"Data integrity issues found: {len(failed)}")
        for item, reason in failed:
            print(f"  - {item}: {reason}")
        raise SystemExit(1)

    print("Data integrity check passed!")


def fetch_state_samples(supabase_url: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    player_stats_rows: list[dict[str, Any]] = []
    offset = 0

    while len(player_stats_rows) < STATE_SAMPLE_SIZE:
        stats_resp = request_with_retry(
            "GET",
            f"{supabase_url}/rest/v1/regional_elo_player_stats",
            headers=headers,
            params={
                "select": "region_type,region_key,player_id,games_played,wins,draws,losses",
                "order": "games_played.desc",
                "limit": PAGE_SIZE,
                "offset": offset,
            },
            timeout=30,
        )
        if stats_resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch regional Elo player stats sample: {response_failure(stats_resp)}"
            )

        page_rows = stats_resp.json()
        player_stats_rows.extend(
            row for row in page_rows if row.get("region_type") == "state" and row.get("games_played", 0) > 0
        )

        if len(page_rows) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    return player_stats_rows[:STATE_SAMPLE_SIZE]


def validate_regional_elo_consistency() -> None:
    supabase_url, _ = get_supabase_env()
    headers = supabase_headers()
    stat_rows = fetch_state_samples(supabase_url, headers)

    if not stat_rows:
        raise SystemExit("No regional Elo player stats rows found to validate.")

    failures: list[tuple[dict[str, Any], str]] = []
    for row in stat_rows:
        stats_resp = request_with_retry(
            "GET",
            f"{supabase_url}/rest/v1/regional_elo_state_activity",
            headers=headers,
            params={
                "select": "games_lifetime,wins,draws,losses",
                "region_type": f"eq.{row['region_type']}",
                "region_key": f"eq.{row['region_key']}",
                "player_id": f"eq.{row['player_id']}",
                "is_primary_state": "eq.true",
            },
            timeout=30,
        )
        if stats_resp.status_code != 200:
            failures.append((row, f"failed to fetch canonical state activity: {response_failure(stats_resp)}"))
            continue

        stats_rows = stats_resp.json()
        if not stats_rows:
            failures.append((row, "missing primary state activity row"))
            continue

        stats = stats_rows[0]
        comparisons = (
            ("games_played", "games_lifetime"),
            ("wins", "wins"),
            ("draws", "draws"),
            ("losses", "losses"),
        )
        for observed_field, canonical_field in comparisons:
            if row[observed_field] != stats[canonical_field]:
                failures.append(
                    (
                        row,
                        f"{observed_field}: player_stats={row[observed_field]} "
                        f"state_activity={stats[canonical_field]}",
                    )
                )
                break

    if failures:
        print("Regional Elo aggregate consistency check failed:")
        for row, reason in failures:
            print(f"  - {row['region_key']} / {row['player_id']}: {reason}")
        raise SystemExit(1)

    print(f"Validated {len(stat_rows)} regional Elo player stats rows against primary state activity.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run backend maintenance validations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("views", help="Validate backend views and RPC functions")
    subparsers.add_parser("data-integrity", help="Validate baseline data counts")
    subparsers.add_parser("regional-elo", help="Validate regional Elo consistency")
    subparsers.add_parser("all", help="Run all backend maintenance validations")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "views":
        validate_views()
    elif args.command == "data-integrity":
        validate_data_integrity()
    elif args.command == "regional-elo":
        validate_regional_elo_consistency()
    elif args.command == "all":
        validate_views()
        validate_data_integrity()
        validate_regional_elo_consistency()
    else:  # pragma: no cover - argparse enforces valid commands
        raise SystemExit(f"Unknown command: {args.command}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
