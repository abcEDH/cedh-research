#!/usr/bin/env python3
"""Compute the global Elo leaderboard and derived state activity.

Usage:
  python src/regional_elo.py
"""

from __future__ import annotations

import os
import time
import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ingest import SupabaseClient

K_FACTOR = 30
DEFAULT_RATING = 1500.0
ELO_BASE = 2
ELO_DIVISOR = 200
GLOBAL_REGION_TYPE = "global"
GLOBAL_REGION_KEY = "ALL"
STATE_REGION_TYPE = "state"
GLOBAL_ELO_RATINGS_TABLE_CANDIDATES = ("global_elo_ratings", "regional_elo_ratings")
GAME_RESULTS_TABLE_CANDIDATES = ("global_elo_game_results", "regional_elo_game_results")
COMMANDER_PRIMARY_LOOKBACK_MONTHS = 6
COMMANDER_FALLBACK_LOOKBACK_MONTHS = 12
COMMANDER_MIN_PRIMARY_ENTRIES = 2
COMMANDER_RECENCY_HALF_LIFE_DAYS = 15
ACTIVE_PLAYER_LOOKBACK_MONTHS = 6
REGION_COUNTRY_BY_STATE = {
    "AGDER": "NORWAY",
    "ALABAMA": "UNITED STATES",
    "ALBERTA": "CANADA",
    "ANDALUCÍA": "SPAIN",
    "ANDALUSIA": "SPAIN",
    "ANDORRA LA VELLA": "ANDORRA",
    "ANTOFAGASTA": "CHILE",
    "ARAGÓN": "SPAIN",
    "ARAUCANÍA": "CHILE",
    "ARIZONA": "UNITED STATES",
    "ARKANSAS": "UNITED STATES",
    "AUCKLAND": "NEW ZEALAND",
    "BADEN-WURTTEMBERG": "GERMANY",
    "BADEN-WÜRTTEMBERG": "GERMANY",
    "BAJA CALIFORNIA": "MEXICO",
    "BANGKOK": "THAILAND",
    "BASQUE COUNTRY": "SPAIN",
    "BAVARIA": "GERMANY",
    "BAYERN": "GERMANY",
    "BERLIN": "GERMANY",
    "BERN": "SWITZERLAND",
    "BÍO BÍO": "CHILE",
    "BOGOTA": "COLOMBIA",
    "BOGOTÁ": "COLOMBIA",
    "BRAGA": "PORTUGAL",
    "BRITISH COLUMBIA": "CANADA",
    "BUCUREȘTI": "ROMANIA",
    "CALABARZON": "PHILIPPINES",
    "CALIFORNIA": "UNITED STATES",
    "CANARIAS": "SPAIN",
    "CAROLINA": "PUERTO RICO",
    "CATALONIA": "SPAIN",
    "CATALUÑA": "SPAIN",
    "CATALUNYA": "SPAIN",
    "CDMX": "MEXICO",
    "CENTRAL BOHEMIAN REGION": "CZECHIA",
    "CIUDAD AUTÓNOMA DE BUENOS AIRES": "ARGENTINA",
    "CIUDAD DE MÉXICO": "MEXICO",
    "COIMBRA": "PORTUGAL",
    "COLORADO": "UNITED STATES",
    "COMUNIDAD DE MADRID": "SPAIN",
    "COMUNIDAD VALENCIANA": "SPAIN",
    "CONNECTICUT": "UNITED STATES",
    "COQUIMBO": "CHILE",
    "COUNTY DUBLIN": "IRELAND",
    "DELAWARE": "UNITED STATES",
    "DISTRICT OF COLUMBIA": "UNITED STATES",
    "DISTRITO DE ÉVORA": "PORTUGAL",
    "DUBAI": "UNITED ARAB EMIRATES",
    "EMILIA-ROMAGNA": "ITALY",
    "ENGLAND": "UNITED KINGDOM",
    "ESTADO DE MÉXICO": "MEXICO",
    "EUSKADI": "SPAIN",
    "FEDERAL TERRITORY OF KUALA LUMPUR": "MALAYSIA",
    "FLORIDA": "UNITED STATES",
    "FRIESLAND": "NETHERLANDS",
    "GAUTENG": "SOUTH AFRICA",
    "GELDERLAND": "NETHERLANDS",
    "GEORGIA": "UNITED STATES",
    "GUANGDONG PROVINCE": "CHINA",
    "GUATEMALA": "GUATEMALA",
    "GUAYANILLA": "PUERTO RICO",
    "HAMBURG": "GERMANY",
    "HAWAII": "UNITED STATES",
    "HESSE": "GERMANY",
    "HLAVNÍ MĚSTO PRAHA": "CZECHIA",
    "IDAHO": "UNITED STATES",
    "ÎLE-DE-FRANCE": "FRANCE",
    "ILLINOIS": "UNITED STATES",
    "INDIANA": "UNITED STATES",
    "IOWA": "UNITED STATES",
    "JAL.": "MEXICO",
    "JALISCO": "MEXICO",
    "JAWA BARAT": "INDONESIA",
    "JIANG SU SHENG": "CHINA",
    "JOHOR": "MALAYSIA",
    "JUDEȚUL CLUJ": "ROMANIA",
    "JUDEȚUL TIMIȘ": "ROMANIA",
    "KANAGAWA": "JAPAN",
    "KANSAS": "UNITED STATES",
    "KANTA-HÄME": "FINLAND",
    "KAOHSIUNG CITY": "TAIWAN",
    "KENTUCKY": "UNITED STATES",
    "KÓPAVOGSBÆR": "ICELAND",
    "KRÁLOVÉHRADECKÝ KRAJ": "CZECHIA",
    "KRUNG THEP MAHA NAKHON": "THAILAND",
    "KYIV": "UKRAINE",
    "KZN": "SOUTH AFRICA",
    "LAZIO": "ITALY",
    "LEIRIA DISTRICT": "PORTUGAL",
    "LESSER POLAND VOIVODESHIP": "POLAND",
    "LËTZEBUERG": "LUXEMBOURG",
    "LIGURIA": "ITALY",
    "LISBOA": "PORTUGAL",
    "LISBON": "PORTUGAL",
    "LOMBARDIA": "ITALY",
    "LOUISIANA": "UNITED STATES",
    "MAINE": "UNITED STATES",
    "MANITOBA": "CANADA",
    "MARYLAND": "UNITED STATES",
    "MASOVIAN VOIVODESHIP": "POLAND",
    "MASSACHUSETTS": "UNITED STATES",
    "MERSCH": "LUXEMBOURG",
    "METRO MANILA": "PHILIPPINES",
    "MÉX.": "MEXICO",
    "MICHIGAN": "UNITED STATES",
    "MINAS GERAIS": "BRAZIL",
    "MINNESOTA": "UNITED STATES",
    "MINSK REGION": "BELARUS",
    "MISSISSIPPI": "UNITED STATES",
    "MISSOURI": "UNITED STATES",
    "MONTANA": "UNITED STATES",
    "MOSCOW": "RUSSIA",
    "NAVARRA": "SPAIN",
    "NCR": "PHILIPPINES",
    "NDS": "GERMANY",
    "NEBRASKA": "UNITED STATES",
    "NEVADA": "UNITED STATES",
    "NEW HAMPSHIRE": "UNITED STATES",
    "NEW JERSEY": "UNITED STATES",
    "NEW MEXICO": "UNITED STATES",
    "NEW SOUTH WALES": "AUSTRALIA",
    "NEW YORK": "UNITED STATES",
    "NIEDERSACHSEN": "GERMANY",
    "NOORD-BRABANT": "NETHERLANDS",
    "NOORD-HOLLAND": "NETHERLANDS",
    "NORDRHEIN-WESTFALEN": "GERMANY",
    "NORTH BRABANT": "NETHERLANDS",
    "NORTH CAROLINA": "UNITED STATES",
    "NORTH DAKOTA": "UNITED STATES",
    "NORTH HOLLAND": "NETHERLANDS",
    "NRW": "GERMANY",
    "NSW": "AUSTRALIA",
    "NUEVO LEÓN": "MEXICO",
    "OBERÖSTERREICH": "AUSTRIA",
    "OCCITANIE": "FRANCE",
    "OHIO": "UNITED STATES",
    "OKLAHOMA": "UNITED STATES",
    "ONTARIO": "CANADA",
    "OREGON": "UNITED STATES",
    "PAÍS VASCO": "SPAIN",
    "PARANÁ": "BRAZIL",
    "PARDUBICKÝ KRAJ": "CZECHIA",
    "PENNSYLVANIA": "UNITED STATES",
    "PIEMONTE": "ITALY",
    "PIRKANMAA": "FINLAND",
    "PLZEŇ REGION": "CZECHIA",
    "PLZEŇSKÝ KRAJ": "CZECHIA",
    "POHJOIS-SAVO": "FINLAND",
    "PROVINCIA DE BUENOS AIRES": "ARGENTINA",
    "PROVINCIA DE CARTAGO": "COSTA RICA",
    "PUEBLA": "MEXICO",
    "QLD": "AUSTRALIA",
    "QUEBEC": "CANADA",
    "QUÉBEC": "CANADA",
    "QUEENSLAND": "AUSTRALIA",
    "REGIÓN DE MURCIA": "SPAIN",
    "REGIÓN METROPOLITANA": "CHILE",
    "RÉGION WALLONNE": "BELGIUM",
    "RHEINLAND-PFALZ": "GERMANY",
    "RHINELAND-PALATINATE": "GERMANY",
    "RHODE ISLAND": "UNITED STATES",
    "RIO DE JANEIRO": "BRAZIL",
    "RIO GRANDE DO SUL": "BRAZIL",
    "RÍO NEGRO": "ARGENTINA",
    "RIYADH PROVINCE": "SAUDI ARABIA",
    "SAARLAND": "GERMANY",
    "SACHSEN": "GERMANY",
    "SAN JUAN": "PUERTO RICO",
    "SAN SALVADOR": "EL SALVADOR",
    "SAN SALVADOR DEPARTMENT": "EL SALVADOR",
    "SANKT-PETERBURG": "RUSSIA",
    "SANT JULIÀ DE LÒRIA": "ANDORRA",
    "SANTARÉM": "PORTUGAL",
    "SANTIAGO METROPOLITAN REGION": "CHILE",
    "SAO PAULO": "BRAZIL",
    "SÃO PAULO": "BRAZIL",
    "SAXONY": "GERMANY",
    "SCHLESWIG-HOLSTEIN": "GERMANY",
    "SCOTLAND": "UNITED KINGDOM",
    "SELANGOR": "MALAYSIA",
    "SETUBAL": "PORTUGAL",
    "SETÚBAL": "PORTUGAL",
    "SHANG HAI SHI": "CHINA",
    "SICILIA": "ITALY",
    "SKÅNE LÄN": "SWEDEN",
    "SOFIA CITY PROVINCE": "BULGARIA",
    "SOUTH CAROLINA": "UNITED STATES",
    "SOUTH DAKOTA": "UNITED STATES",
    "STOCKHOLMS LÄN": "SWEDEN",
    "STŘEDOČESKÝ KRAJ": "CZECHIA",
    "TAINAN CITY": "TAIWAN",
    "TAOYUAN CITY": "TAIWAN",
    "TARAPACÁ": "CHILE",
    "TASMANIA": "AUSTRALIA",
    "TENNESSEE": "UNITED STATES",
    "TEXAS": "UNITED STATES",
    "TOSCANA": "ITALY",
    "UPRAVNA ENOTA MARIBOR": "SLOVENIA",
    "UTAH": "UNITED STATES",
    "UTRECHT": "NETHERLANDS",
    "UUSIMAA": "FINLAND",
    "VALENCIAN COMMUNITY": "SPAIN",
    "VALPARAÍSO": "CHILE",
    "VARSINAIS-SUOMI": "FINLAND",
    "VENETO": "ITALY",
    "VERMONT": "UNITED STATES",
    "VIC": "AUSTRALIA",
    "VICTORIA": "AUSTRALIA",
    "VIRGINIA": "UNITED STATES",
    "VLAAMS GEWEST": "BELGIUM",
    "VLAANDEREN": "BELGIUM",
    "WALES": "UNITED KINGDOM",
    "WASHINGTON": "UNITED STATES",
    "WEST BENGAL": "INDIA",
    "WEST VIRGINIA": "UNITED STATES",
    "WESTERN AUSTRALIA": "AUSTRALIA",
    "WESTERN CAPE": "SOUTH AFRICA",
    "WIEN": "AUSTRIA",
    "WILAYAH PERSEKUTUAN KUALA LUMPUR": "MALAYSIA",
    "WISCONSIN": "UNITED STATES",
    "WOJEWÓDZTWO MAŁOPOLSKIE": "POLAND",
    "WOJEWÓDZTWO MAZOWIECKIE": "POLAND",
    "WOJEWÓDZTWO WIELKOPOLSKIE": "POLAND",
    "WYOMING": "UNITED STATES",
    "YUC.": "MEXICO",
    "YUCATÁN": "MEXICO",
    "ZAGREBAČKA ŽUPANIJA": "CROATIA",
    "ГРОДНЕНСКАЯ ОБЛАСТЬ": "BELARUS",
    "МИНСКАЯ ОБЛАСТЬ": "BELARUS",
    "МОСКВА": "RUSSIA",
    "上海市": "CHINA",
    "广东省": "CHINA",
    "東京都": "JAPAN",
    "高雄市": "TAIWAN",
}


@dataclass
class PlayerStats:
    rating: float = DEFAULT_RATING
    games: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    last_game_date: str | None = None


@dataclass
class StateActivity:
    country_key: str | None = None
    games_30d: int = 0
    games_90d: int = 0
    games_365d: int = 0
    games_lifetime: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    last_game_date: str | None = None
    activity_score: float = 0.0
    is_primary_state: bool = False


@dataclass
class CommanderUsage:
    player_id: str
    topdeck_id: str
    player_name: str | None
    commander_name: str
    start_date: str
    decklist_url: str | None = None


def load_credentials() -> tuple[str, str]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        raise SystemExit("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    return supabase_url, supabase_key


# ---------------------------------------------------------------------------
# Job lifecycle helpers for elo_maintenance_jobs tracking
# ---------------------------------------------------------------------------

MAINTENANCE_JOBS_TABLE = "elo_maintenance_jobs"


def claim_job(client: SupabaseClient, job_id: str) -> bool:
    """Transition job from pending/dispatched to running."""
    try:
        now = utc_now().isoformat()
        client.upsert(
            MAINTENANCE_JOBS_TABLE,
            {"id": job_id, "status": "running", "started_at": now, "heartbeat_at": now},
            on_conflict="id",
        )
        return True
    except Exception as exc:
        print(f"Failed to claim job {job_id}: {exc}", flush=True)
        return False


def update_job_heartbeat(client: SupabaseClient, job_id: str) -> None:
    """Best-effort heartbeat so stale-job detection knows we are alive."""
    try:
        client.upsert(
            MAINTENANCE_JOBS_TABLE,
            {"id": job_id, "heartbeat_at": utc_now().isoformat()},
            on_conflict="id",
        )
    except Exception:
        pass


def complete_job(client: SupabaseClient, job_id: str, metrics: dict) -> None:
    """Mark job as completed with output metrics."""
    now = utc_now().isoformat()
    client.upsert(
        MAINTENANCE_JOBS_TABLE,
        {"id": job_id, "status": "completed", "completed_at": now, "heartbeat_at": now, **metrics},
        on_conflict="id",
    )


def fail_job(client: SupabaseClient, job_id: str, error: str) -> None:
    """Mark job as failed with error text."""
    try:
        client.upsert(
            MAINTENANCE_JOBS_TABLE,
            {
                "id": job_id,
                "status": "failed",
                "completed_at": utc_now().isoformat(),
                "error_text": error[:2000],
            },
            on_conflict="id",
        )
    except Exception:
        pass


QueryParams = Mapping[str, Any] | Sequence[Tuple[str, Any]]


def with_paging_params(params: QueryParams, limit: int, offset: int) -> QueryParams:
    page_params = {"limit": limit, "offset": offset}
    if isinstance(params, Mapping):
        return {**params, **page_params}
    return [*params, *page_params.items()]


def fetch_all(client: SupabaseClient, table: str, params: QueryParams, limit: int = 1000) -> List[Dict[str, Any]]:
    offset = 0
    rows: List[Dict[str, Any]] = []
    while True:
        page_params = with_paging_params(params, limit, offset)
        page = client.select(table, page_params)
        if not page:
            break
        rows.extend(page)
        if len(page) < limit:
            break
        offset += limit
        time.sleep(0.05)
    return rows


def in_filter(values: Sequence[str]) -> str:
    return f"in.({','.join(values)})"


def fetch_null_state_game_rows(client: SupabaseClient, start_date: str | None = None) -> List[Dict[str, Any]]:
    """Backfill no-state games until the deployed source view includes them."""
    filters: QueryParams = [
        (
            "select",
            "id,tournament_id,is_draw,table_number,tournaments!inner(start_date,state,country)",
        ),
        ("tournaments.state", "is.null"),
        ("order", "id.asc"),
    ]
    if start_date:
        filters = [*filters, ("tournaments.start_date", f"gte.{start_date}")]

    games = fetch_all(
        client,
        "games",
        filters,
        limit=1000,
    )
    if not games:
        return []

    games_by_id = {row["id"]: row for row in games}
    participants: List[Dict[str, Any]] = []
    game_ids = list(games_by_id.keys())
    for i in range(0, len(game_ids), 250):
        game_id_chunk = game_ids[i : i + 250]
        participants.extend(
            fetch_all(
                client,
                "game_participants",
                [
                    ("select", "game_id,entry_id,result,tournament_entries(player_id)"),
                    ("game_id", in_filter(game_id_chunk)),
                    ("order", "game_id.asc"),
                ],
                limit=1000,
            )
        )

    rows: List[Dict[str, Any]] = []
    for participant in participants:
        game = games_by_id.get(participant.get("game_id"))
        if not game:
            continue
        tournament = game.get("tournaments") or {}
        entry = participant.get("tournament_entries") or {}
        player_id = entry.get("player_id")
        if not player_id:
            continue
        rows.append(
            {
                "game_id": participant["game_id"],
                "tournament_id": game["tournament_id"],
                "entry_id": participant["entry_id"],
                "player_id": player_id,
                "start_date": tournament.get("start_date"),
                "state": tournament.get("state"),
                "country": tournament.get("country"),
                "result": participant.get("result"),
                "is_draw": game.get("is_draw"),
                "table_number": game.get("table_number"),
            }
        )

    print(f"Fetched {len(rows)} no-state game-result rows from raw tables", flush=True)
    return rows


def month_starts(start_year: int, end_year: int) -> Iterable[datetime]:
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            yield datetime(year, month, 1)


def next_month(value: datetime) -> datetime:
    if value.month == 12:
        return datetime(value.year + 1, 1, 1)
    return datetime(value.year, value.month + 1, 1)


def utc_now() -> datetime:
    return datetime.now(UTC)


def table_exists(client: SupabaseClient, table: str) -> bool:
    try:
        client.select(table, {"select": "*", "limit": "1"}, max_retries=1)
        return True
    except Exception:
        return False


def first_available_table(client: SupabaseClient, candidates: Sequence[str]) -> str:
    for table in candidates:
        if table_exists(client, table):
            return table
    raise RuntimeError(f"None of the candidate tables are available: {', '.join(candidates)}")


def fetch_elo_game_rows(client: SupabaseClient, smoke_days: int | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    current_month = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_month = next_month(current_month)
    start_cutoff = (utc_now().date() - timedelta(days=smoke_days)).isoformat() if smoke_days else None
    game_results_table = first_available_table(client, GAME_RESULTS_TABLE_CANDIDATES)
    if game_results_table != GAME_RESULTS_TABLE_CANDIDATES[0]:
        print(
            f"Using fallback game-results table '{game_results_table}' because '{GAME_RESULTS_TABLE_CANDIDATES[0]}' is unavailable.",
            flush=True,
        )

    for start in month_starts(2022, end_month.year):
        if start >= end_month:
            break
        end = next_month(start)
        query_start = max(start.date().isoformat(), start_cutoff) if start_cutoff else start.date().isoformat()
        if query_start >= end.date().isoformat():
            continue
        query_params = [
            (
                "select",
                "game_id,tournament_id,entry_id,player_id,start_date,state,country,result,is_draw,table_number",
            ),
            ("order", "start_date.asc,game_id.asc,table_number.asc"),
            ("start_date", f"gte.{query_start}"),
            ("start_date", f"lt.{end.date().isoformat()}"),
        ]
        page = fetch_all(client, game_results_table, query_params, limit=250)
        rows.extend(page)
        print(f"Fetched {len(page)} game-result rows for {start:%Y-%m}", flush=True)

    raw_null_state_rows = fetch_null_state_game_rows(client, start_cutoff)
    if raw_null_state_rows:
        seen_keys = {(row["game_id"], row["entry_id"]) for row in rows}
        rows.extend(
            row
            for row in raw_null_state_rows
            if (row["game_id"], row["entry_id"]) not in seen_keys
        )

    rows.sort(
        key=lambda row: (
            row.get("start_date") or "",
            row.get("game_id") or "",
            row.get("table_number") or 0,
            row.get("entry_id") or "",
        )
    )
    return rows


def parse_game_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def normalized_state(row: Dict[str, Any]) -> str | None:
    state = (row.get("state") or "").strip()
    return state.upper() if state else None


def normalized_country(row: Dict[str, Any]) -> str | None:
    country = (row.get("country") or "").strip()
    if country:
        return country.upper()
    state = normalized_state(row)
    return REGION_COUNTRY_BY_STATE.get(state or "")


def bucketed_activity_score(activity: StateActivity) -> float:
    games_31_90 = max(activity.games_90d - activity.games_30d, 0)
    games_91_365 = max(activity.games_365d - activity.games_90d, 0)
    return round(
        (1.0 * activity.games_30d)
        + (0.35 * games_31_90)
        + (0.10 * games_91_365)
        + (0.02 * activity.games_lifetime),
        6,
    )


def is_known_commander(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return bool(normalized) and normalized != "unknown commander"


def date_months_ago(reference: date, months: int) -> date:
    month = reference.month - months
    year = reference.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(
        reference.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return date(year, month, day)


def recency_weight(start_date: str, reference: date) -> float:
    parsed = parse_game_date(start_date)
    if not parsed:
        return 0.5
    age_days = max((reference - parsed).days, 0)
    return 0.5 ** (age_days / COMMANDER_RECENCY_HALF_LIFE_DAYS)


def process_game(
    rows: List[Dict[str, Any]],
    global_stats: Dict[str, PlayerStats],
    state_activity: Dict[str, Dict[str, StateActivity]],
    profile_activity: Dict[str, Dict[str, StateActivity]],
    event_rows: List[Dict[str, Any]],
    game_date: str | None,
) -> None:
    if not rows:
        return

    players = [row["player_id"] for row in rows if row.get("player_id")]
    if len(players) < 2:
        return

    if any((row.get("result") or "") == "bye" for row in rows):
        return

    is_draw = any((row.get("result") or "") == "draw" for row in rows) or bool(rows[0].get("is_draw"))
    result_value = 1.0 / len(players) if is_draw else None
    parsed_game_date = parse_game_date(game_date)
    age_days = (utc_now().date() - parsed_game_date).days if parsed_game_date else None
    state_key = normalized_state(rows[0])
    country_key = normalized_country(rows[0])
    profile_region_key = state_key or "UNKNOWN"
    profile_country_key = country_key or "UNKNOWN"

    equities = {}
    total_equity = 0.0
    for player_id in players:
        rating = global_stats[player_id].rating
        equity = ELO_BASE ** (rating / ELO_DIVISOR)
        equities[player_id] = equity
        total_equity += equity

    if total_equity == 0:
        return

    for row in rows:
        player_id = row["player_id"]
        stats = global_stats[player_id]
        expected = equities[player_id] / total_equity
        if is_draw:
            result = result_value
            stats.draws += 1
        else:
            result = 1.0 if row.get("result") == "win" else 0.0
            if result == 1.0:
                stats.wins += 1
            else:
                stats.losses += 1

        before = stats.rating
        delta = K_FACTOR * (result - expected)
        stats.rating += delta
        stats.games += 1
        stats.last_game_date = game_date or stats.last_game_date

        profile_region = profile_activity[player_id][profile_region_key]
        profile_region.country_key = profile_country_key
        profile_region.games_lifetime += 1
        profile_region.last_game_date = game_date or profile_region.last_game_date
        if is_draw:
            profile_region.draws += 1
        elif result == 1.0:
            profile_region.wins += 1
        else:
            profile_region.losses += 1
        if age_days is not None:
            if age_days <= 365:
                profile_region.games_365d += 1
            if age_days <= 90:
                profile_region.games_90d += 1
            if age_days <= 30:
                profile_region.games_30d += 1

        event_rows.append(
            {
                "region_type": GLOBAL_REGION_TYPE,
                "region_key": GLOBAL_REGION_KEY,
                "game_id": row["game_id"],
                "tournament_id": row["tournament_id"],
                "player_id": player_id,
                "entry_id": row["entry_id"],
                "game_date": game_date,
                "game_result": row.get("result") or ("draw" if is_draw else "loss"),
                "is_draw": is_draw,
                "opponent_count": max(len(players) - 1, 0),
                "expected_score": round(expected, 6),
                "actual_score": round(result or 0.0, 6),
                "rating_before": round(before, 6),
                "rating_delta": round(delta, 6),
                "rating_after": round(stats.rating, 6),
            }
        )

        if not state_key:
            continue

        activity = state_activity[player_id][state_key]
        activity.country_key = country_key or activity.country_key
        activity.games_lifetime += 1
        activity.last_game_date = game_date or activity.last_game_date
        if is_draw:
            activity.draws += 1
        elif result == 1.0:
            activity.wins += 1
        else:
            activity.losses += 1

        if age_days is None:
            continue
        if age_days <= 365:
            activity.games_365d += 1
        if age_days <= 90:
            activity.games_90d += 1
        if age_days <= 30:
            activity.games_30d += 1


def build_upsert_rows(
    region_type: str,
    region_key: str,
    region_stats: Dict[str, PlayerStats],
) -> List[Dict[str, Any]]:
    updated_at = utc_now().isoformat()
    rows = []
    for player_id, stats in region_stats.items():
        rows.append(
            {
                "region_type": region_type,
                "region_key": region_key,
                "player_id": player_id,
                "rating": round(stats.rating, 3),
                "games_played": stats.games,
                "wins": stats.wins,
                "draws": stats.draws,
                "losses": stats.losses,
                "last_game_date": stats.last_game_date,
                "updated_at": updated_at,
            }
        )
    return rows


def compute_global_elo(smoke_days: int | None = None) -> tuple[
    Dict[str, PlayerStats],
    Dict[str, Dict[str, StateActivity]],
    Dict[str, Dict[str, StateActivity]],
    List[Dict[str, Any]],
]:
    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    rows = fetch_elo_game_rows(client, smoke_days=smoke_days)

    global_stats: Dict[str, PlayerStats] = defaultdict(PlayerStats)
    state_activity: Dict[str, Dict[str, StateActivity]] = defaultdict(lambda: defaultdict(StateActivity))
    profile_activity: Dict[str, Dict[str, StateActivity]] = defaultdict(lambda: defaultdict(StateActivity))
    event_rows: List[Dict[str, Any]] = []
    current_game_id: str | None = None
    buffer: List[Dict[str, Any]] = []
    current_game_date: str | None = None

    for row in rows:
        game_id = row["game_id"]
        if current_game_id is None:
            current_game_id = game_id
            current_game_date = row.get("start_date")

        if game_id != current_game_id:
            process_game(buffer, global_stats, state_activity, profile_activity, event_rows, current_game_date)
            buffer = []
            current_game_id = game_id
            current_game_date = row.get("start_date")

        buffer.append(row)

    if buffer:
        process_game(buffer, global_stats, state_activity, profile_activity, event_rows, current_game_date)

    for activity_group in (state_activity, profile_activity):
        for player_states in activity_group.values():
            primary_state: str | None = None
            primary_sort_key: tuple[float, str, int, int, str] | None = None
            for region_key, activity in player_states.items():
                activity.activity_score = bucketed_activity_score(activity)
                if region_key == "UNKNOWN":
                    continue
                sort_key = (
                    activity.activity_score,
                    activity.last_game_date or "",
                    activity.games_30d,
                    activity.games_lifetime,
                    region_key,
                )
                if primary_sort_key is None or sort_key > primary_sort_key:
                    primary_sort_key = sort_key
                    primary_state = region_key
            if primary_state:
                player_states[primary_state].is_primary_state = True

    return global_stats, state_activity, profile_activity, event_rows


def build_primary_state_by_player(
    state_activity: Dict[str, Dict[str, StateActivity]]
) -> Dict[str, Tuple[str, StateActivity]]:
    primary_by_player: Dict[str, Tuple[str, StateActivity]] = {}
    for player_id, player_states in state_activity.items():
        primary_state: str | None = None
        primary_activity: StateActivity | None = None
        for region_key, activity in player_states.items():
            if activity.is_primary_state:
                primary_state = region_key
                primary_activity = activity
                break
        if primary_state and primary_activity:
            primary_by_player[player_id] = (primary_state, primary_activity)
    return primary_by_player


def build_state_activity_rows(state_activity: Dict[str, Dict[str, StateActivity]]) -> List[Dict[str, Any]]:
    updated_at = utc_now().isoformat()
    rows: List[Dict[str, Any]] = []
    for player_id, state_rows in state_activity.items():
        for region_key, activity in state_rows.items():
            rows.append(
                {
                    "region_type": STATE_REGION_TYPE,
                    "region_key": region_key,
                    "country_key": activity.country_key,
                    "player_id": player_id,
                    "games_30d": activity.games_30d,
                    "games_90d": activity.games_90d,
                    "games_365d": activity.games_365d,
                    "games_lifetime": activity.games_lifetime,
                    "wins": activity.wins,
                    "draws": activity.draws,
                    "losses": activity.losses,
                    "last_game_date": activity.last_game_date,
                    "activity_score": activity.activity_score,
                    "is_primary_state": activity.is_primary_state,
                    "updated_at": updated_at,
                }
            )
    return rows


def fetch_players_by_id(client: SupabaseClient, player_ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i in range(0, len(player_ids), 250):
        player_id_chunk = player_ids[i : i + 250]
        rows.extend(
            fetch_all(
                client,
                "players",
                [
                    ("select", "id,name,topdeck_id"),
                    ("id", in_filter(player_id_chunk)),
                ],
                limit=1000,
            )
        )
    return {row["id"]: row for row in rows if row.get("id")}


def is_active_player(stats: PlayerStats, cutoff: str) -> bool:
    return bool(stats.last_game_date and stats.last_game_date >= cutoff)


def active_leaderboard_sort_key(row: Dict[str, Any]) -> tuple[float, int, str]:
    return (
        -float(row["rating"]),
        -int(row["games_played"]),
        str(row["player_name"]),
    )


def rank_active_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sorted_rows = sorted(rows, key=active_leaderboard_sort_key)
    for index, row in enumerate(sorted_rows, start=1):
        row["rank"] = index
    return sorted_rows


def build_active_leaderboard_rows(
    global_stats: Dict[str, PlayerStats],
    state_activity: Dict[str, Dict[str, StateActivity]],
    players_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    updated_at = utc_now().isoformat()
    cutoff = date_months_ago(utc_now().date(), ACTIVE_PLAYER_LOOKBACK_MONTHS).isoformat()
    primary_state_by_player = build_primary_state_by_player(state_activity)
    rows_by_scope: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for player_id, stats in global_stats.items():
        if not is_active_player(stats, cutoff):
            continue
        player = players_by_id.get(player_id) or {}
        player_name = player.get("name") or "Unknown"
        topdeck_id = player.get("topdeck_id")
        primary_region_key: str | None = None
        primary_country_key: str | None = None
        primary_activity_score: float | None = None
        primary = primary_state_by_player.get(player_id)
        if primary:
            primary_region_key, primary_activity = primary
            primary_country_key = primary_activity.country_key
            primary_activity_score = primary_activity.activity_score

        base_row = {
            "player_id": player_id,
            "player_name": player_name,
            "topdeck_id": topdeck_id,
            "rating": round(stats.rating, 3),
            "games_played": stats.games,
            "wins": stats.wins,
            "draws": stats.draws,
            "losses": stats.losses,
            "last_game_date": stats.last_game_date,
            "primary_country_key": primary_country_key,
            "primary_region_key": primary_region_key,
            "updated_at": updated_at,
        }
        rows_by_scope[(GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY)].append(
            {
                **base_row,
                "region_type": GLOBAL_REGION_TYPE,
                "region_key": GLOBAL_REGION_KEY,
                "country_key": None,
                "activity_score": None,
            }
        )
        if primary_region_key and primary_country_key:
            rows_by_scope[("country", primary_country_key)].append(
                {
                    **base_row,
                    "region_type": "country",
                    "region_key": primary_country_key,
                    "country_key": primary_country_key,
                    "activity_score": primary_activity_score,
                }
            )
            rows_by_scope[(STATE_REGION_TYPE, primary_region_key)].append(
                {
                    **base_row,
                    "region_type": STATE_REGION_TYPE,
                    "region_key": primary_region_key,
                    "country_key": primary_country_key,
                    "activity_score": primary_activity_score,
                }
            )

    ranked_rows: List[Dict[str, Any]] = []
    for rows in rows_by_scope.values():
        ranked_rows.extend(rank_active_rows(rows))
    return ranked_rows


def build_profile_summary_rows(
    global_stats: Dict[str, PlayerStats],
    profile_activity: Dict[str, Dict[str, StateActivity]],
    players_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    updated_at = utc_now().isoformat()
    rows: List[Dict[str, Any]] = []
    for player_id, stats in global_stats.items():
        player = players_by_id.get(player_id) or {}
        player_name = player.get("name") or "Unknown"
        state_rows = []
        home_region_key: str | None = None
        home_country_key: str | None = None
        for region_key, activity in profile_activity.get(player_id, {}).items():
            state_rows.append(
                {
                    "country_key": activity.country_key or "UNKNOWN",
                    "region_key": region_key,
                    "games_played": activity.games_lifetime,
                    "wins": activity.wins,
                    "draws": activity.draws,
                    "losses": activity.losses,
                    "last_game_date": activity.last_game_date,
                    "activity_score": activity.activity_score,
                    "is_primary_state": activity.is_primary_state,
                }
            )
            if activity.is_primary_state:
                home_region_key = region_key
                home_country_key = activity.country_key

        state_rows.sort(
            key=lambda row: (
                row["region_key"] == "UNKNOWN",
                -int(row["games_played"]),
                str(row["country_key"]),
                str(row["region_key"]),
            )
        )
        rows.append(
            {
                "player_id": player_id,
                "topdeck_id": player.get("topdeck_id"),
                "player_name": player_name,
                "games_played": stats.games,
                "wins": stats.wins,
                "draws": stats.draws,
                "losses": stats.losses,
                "last_game_date": stats.last_game_date,
                "home_country_key": home_country_key,
                "home_region_key": home_region_key,
                "state_assignments": state_rows,
                "updated_at": updated_at,
            }
        )
    return rows


def fetch_commander_usage_rows(client: SupabaseClient) -> Dict[str, List[CommanderUsage]]:
    rows = fetch_all(
        client,
        "player_commander_entries",
        [
            (
                "select",
                "player_id,topdeck_id,player_name,commander_name,start_date,decklist_url",
            ),
            ("topdeck_id", "not.is.null"),
            ("commander_name", "not.is.null"),
            ("start_date", "not.is.null"),
            ("order", "start_date.asc"),
        ],
        limit=1000,
    )

    by_topdeck_id: Dict[str, List[CommanderUsage]] = defaultdict(list)
    for row in rows:
        topdeck_id = (row.get("topdeck_id") or "").strip()
        commander_name = (row.get("commander_name") or "").strip()
        start_date = row.get("start_date")
        player_id = row.get("player_id")
        if not topdeck_id or not player_id or not start_date or not is_known_commander(commander_name):
            continue
        by_topdeck_id[topdeck_id].append(
            CommanderUsage(
                player_id=player_id,
                topdeck_id=topdeck_id,
                player_name=row.get("player_name"),
                commander_name=commander_name,
                start_date=str(start_date),
                decklist_url=row.get("decklist_url"),
            )
        )

    print(f"Fetched commander history for {len(by_topdeck_id)} players", flush=True)
    return by_topdeck_id


def resilient_delete(client: SupabaseClient, table: str, fallback_table: str, filters: Dict[str, Any]) -> None:
    try:
        client.delete(table, filters)
    except Exception as exc:
        print(f"Delete failed for {table}, trying {fallback_table}. Error: {exc}", flush=True)
        try:
            client.delete(fallback_table, filters)
        except Exception as exc2:
            print(f"Delete failed for fallback {fallback_table}. Error: {exc2}", flush=True)
            raise RuntimeError(
                f"resilient_delete: both {table} and {fallback_table} failed"
            ) from exc2


def resilient_upsert(
    client: SupabaseClient,
    table: str,
    fallback_table: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
    delete_filters: Dict[str, Any] | None = None,
) -> None:
    try:
        upsert_rows(client, table, rows, on_conflict=on_conflict)
    except Exception as exc:
        print(f"Upsert failed for {table}, trying {fallback_table}. Error: {exc}", flush=True)
        if delete_filters is not None:
            try:
                client.delete(fallback_table, delete_filters)
            except Exception as del_exc:
                print(f"Could not pre-clear {fallback_table} before fallback upsert: {del_exc}", flush=True)
        try:
            upsert_rows(client, fallback_table, rows, on_conflict=on_conflict)
        except Exception as exc2:
            print(f"Upsert failed for fallback {fallback_table}. Error: {exc2}", flush=True)
            raise RuntimeError(
                f"resilient_upsert: both {table} and {fallback_table} failed"
            ) from exc2


def upsert_state_activity_rows(
    client: SupabaseClient,
    table: str,
    fallback_table: str,
    rows: List[Dict[str, Any]],
    on_conflict: str,
    delete_filters: Dict[str, Any] | None = None,
) -> None:
    """Upsert state-activity rows with a country_key-stripping fallback for pre-migration schemas."""
    stripped = [{k: v for k, v in row.items() if k != "country_key"} for row in rows]
    try:
        upsert_rows(client, table, rows, on_conflict=on_conflict)
        return
    except Exception as exc:
        print(
            f"State-activity upsert failed for {table} (with country_key), retrying without. Error: {exc}",
            flush=True,
        )
    try:
        upsert_rows(client, table, stripped, on_conflict=on_conflict)
        return
    except Exception as exc:
        print(
            f"State-activity upsert failed for {table} (stripped), trying {fallback_table}. Error: {exc}",
            flush=True,
        )
    if delete_filters is not None:
        try:
            client.delete(fallback_table, delete_filters)
        except Exception as del_exc:
            print(f"Could not pre-clear {fallback_table} before fallback upsert: {del_exc}", flush=True)
    try:
        upsert_rows(client, fallback_table, stripped, on_conflict=on_conflict)
    except Exception as exc:
        raise RuntimeError(
            f"upsert_state_activity_rows: all paths failed for {table} and {fallback_table}"
        ) from exc


def selected_commander_rows(rows: List[CommanderUsage], reference: date) -> List[CommanderUsage]:
    primary_start = date_months_ago(reference, COMMANDER_PRIMARY_LOOKBACK_MONTHS).isoformat()
    fallback_start = date_months_ago(reference, COMMANDER_FALLBACK_LOOKBACK_MONTHS).isoformat()
    primary_rows = [row for row in rows if row.start_date >= primary_start]
    if len(primary_rows) >= COMMANDER_MIN_PRIMARY_ENTRIES:
        return primary_rows

    fallback_rows = [
        row
        for row in rows
        if fallback_start <= row.start_date < primary_start
    ]
    if primary_rows or fallback_rows:
        return [*primary_rows, *fallback_rows]

    return rows[-1:] if rows else []


def build_commander_profile_rows(client: SupabaseClient) -> List[Dict[str, Any]]:
    by_topdeck_id = fetch_commander_usage_rows(client)
    updated_at = utc_now().isoformat()
    reference = utc_now().date()
    profile_rows: List[Dict[str, Any]] = []

    for topdeck_id, rows in by_topdeck_id.items():
        rows.sort(key=lambda row: row.start_date)
        profile_rows_for_prediction = selected_commander_rows(rows, reference)
        per_commander: Dict[str, Dict[str, Any]] = {}

        for row in profile_rows_for_prediction:
            current = per_commander.get(row.commander_name) or {
                "commander": row.commander_name,
                "entries": 0,
                "prediction_score": 0.0,
                "latest_date": None,
                "latest_decklist_date": None,
                "latest_decklist_url": None,
            }
            current["entries"] += 1
            current["prediction_score"] += recency_weight(row.start_date, reference)
            if not current["latest_date"] or row.start_date > current["latest_date"]:
                current["latest_date"] = row.start_date
            if row.decklist_url and (
                not current["latest_decklist_date"] or row.start_date >= current["latest_decklist_date"]
            ):
                current["latest_decklist_date"] = row.start_date
                current["latest_decklist_url"] = row.decklist_url
            per_commander[row.commander_name] = current

        sorted_commanders = sorted(
            per_commander.values(),
            key=lambda row: (
                row["prediction_score"],
                row["entries"],
                row["latest_date"] or "",
                row["commander"],
            ),
            reverse=True,
        )
        total_prediction_score = sum(row["prediction_score"] for row in sorted_commanders)
        total_entries = sum(row["entries"] for row in sorted_commanders)
        commander_predictions = [
            {
                "commander": row["commander"],
                "entries": row["entries"],
                "prediction_score": round(row["prediction_score"], 6),
                "prediction_share": round(
                    row["prediction_score"] / total_prediction_score,
                    6,
                )
                if total_prediction_score
                else 0,
                "latest_date": row["latest_date"],
                "latest_decklist_url": row["latest_decklist_url"],
            }
            for row in sorted_commanders[:3]
        ]
        latest_row = rows[-1]
        active = commander_predictions[0] if commander_predictions else None

        profile_rows.append(
            {
                "player_id": latest_row.player_id,
                "topdeck_id": topdeck_id,
                "player_name": latest_row.player_name,
                "active_commander": active["commander"] if active else None,
                "active_commander_entries": active["entries"] if active else 0,
                "active_commander_prediction_score": active["prediction_score"] if active else 0,
                "total_entries": total_entries,
                "commander_predictions": commander_predictions,
                "latest_commander": latest_row.commander_name,
                "latest_commander_date": latest_row.start_date,
                "latest_decklist_url": latest_row.decklist_url,
                "updated_at": updated_at,
            }
        )

    return profile_rows


def upsert_rows(client: SupabaseClient, table: str, rows: List[Dict[str, Any]], on_conflict: str) -> None:
    if not rows:
        print(f"No rows to upsert for {table}.")
        return

    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.upsert(table, batch, on_conflict=on_conflict)
        print(f"Upserted {len(batch)} rows into {table}")


def dedupe_rows(rows: List[Dict[str, Any]], keys: Sequence[str]) -> List[Dict[str, Any]]:
    deduped: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for row in rows:
        deduped[tuple(row.get(key) for key in keys)] = row
    return list(deduped.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute global Elo and derived state activity leaderboards")
    parser.add_argument(
        "--smoke-days",
        type=int,
        default=None,
        help="Limit recompute inputs to tournaments from the last N days for PR-safe smoke checks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute output rows without writing leaderboard tables back to Supabase.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write recompute output back to Supabase. Required for live refreshes.",
    )
    args = parser.parse_args()

    if args.smoke_days is not None and args.apply:
        raise SystemExit("--smoke-days cannot be combined with --apply; smoke runs are validation-only.")
    if not args.dry_run and not args.apply:
        raise SystemExit("Live writes require --apply; use --dry-run for validation.")

    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    global_stats, state_activity, profile_activity, event_rows = compute_global_elo(smoke_days=args.smoke_days)
    event_rows = dedupe_rows(event_rows, ["region_type", "region_key", "game_id", "player_id"])
    rating_rows = build_upsert_rows(GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY, global_stats)
    state_activity_rows = build_state_activity_rows(state_activity)
    players_by_id = fetch_players_by_id(client, list(global_stats.keys()))
    active_leaderboard_rows = build_active_leaderboard_rows(global_stats, state_activity, players_by_id)
    profile_summary_rows = build_profile_summary_rows(global_stats, profile_activity, players_by_id)

    if not rating_rows:
        raise SystemExit("Refusing to clear Regional Elo rows because no global rating rows were computed.")

    if args.dry_run:
        print(
            "regional_elo dry-run:",
            f"ratings={len(rating_rows)}",
            f"state_rows={len(state_activity_rows)}",
            f"event_rows={len(event_rows)}",
            f"active_leaderboard_rows={len(active_leaderboard_rows)}",
            f"profile_summary_rows={len(profile_summary_rows)}",
        )
        return

    commander_profile_rows = build_commander_profile_rows(client)

    ratings_table = first_available_table(client, GLOBAL_ELO_RATINGS_TABLE_CANDIDATES)
    if ratings_table != GLOBAL_ELO_RATINGS_TABLE_CANDIDATES[0]:
        print(
            f"Using fallback ratings table '{ratings_table}' because '{GLOBAL_ELO_RATINGS_TABLE_CANDIDATES[0]}' is unavailable.",
            flush=True,
        )

    print("Deleting existing global Elo, state activity, and event rows")
    resilient_delete(client, ratings_table, "regional_elo_ratings", {"region_type": f"eq.{GLOBAL_REGION_TYPE}"})
    resilient_delete(client, "global_elo_state_activity", "regional_elo_state_activity", {"region_type": f"eq.{STATE_REGION_TYPE}"})
    resilient_delete(client, "global_elo_game_events", "regional_elo_game_events", {"region_type": f"eq.{GLOBAL_REGION_TYPE}"})

    resilient_upsert(
        client,
        ratings_table,
        "regional_elo_ratings",
        rating_rows,
        on_conflict="region_type,region_key,player_id",
        delete_filters={"region_type": f"eq.{GLOBAL_REGION_TYPE}"},
    )
    upsert_state_activity_rows(
        client,
        "global_elo_state_activity",
        "regional_elo_state_activity",
        state_activity_rows,
        on_conflict="region_type,region_key,player_id",
        delete_filters={"region_type": f"eq.{STATE_REGION_TYPE}"},
    )
    resilient_upsert(
        client,
        "global_elo_game_events",
        "regional_elo_game_events",
        event_rows,
        on_conflict="region_type,region_key,game_id,player_id",
        delete_filters={"region_type": f"eq.{GLOBAL_REGION_TYPE}"},
    )

    try:
        client.delete("global_elo_active_leaderboard", {"region_type": "not.is.null"})
        upsert_rows(
            client,
            "global_elo_active_leaderboard",
            active_leaderboard_rows,
            on_conflict="region_type,region_key,player_id",
        )
    except Exception as exc:
        print(
            "Skipping global_elo_active_leaderboard refresh. "
            "Apply the active leaderboard migration to enable it. "
            f"Error: {exc}",
            flush=True,
        )

    try:
        client.delete("global_elo_player_profile_summaries", {"player_id": "not.is.null"})
        upsert_rows(
            client,
            "global_elo_player_profile_summaries",
            profile_summary_rows,
            on_conflict="player_id",
        )
    except Exception as exc:
        print(
            "Skipping global_elo_player_profile_summaries refresh. "
            "Apply the player profile summary migration to enable it. "
            f"Error: {exc}",
            flush=True,
        )

    try:
        client.delete("player_commander_profiles", {"topdeck_id": "not.is.null"})
        upsert_rows(
            client,
            "player_commander_profiles",
            commander_profile_rows,
            on_conflict="player_id",
        )
    except Exception as exc:
        print(
            "Skipping player_commander_profiles refresh. "
            "Apply the player_commander_profiles migration to enable it. "
            f"Error: {exc}",
            flush=True,
        )


if __name__ == "__main__":
    main()
