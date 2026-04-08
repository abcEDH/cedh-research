#!/usr/bin/env python3
"""Compute the global Elo leaderboard and derived state activity.

Usage:
  python src/regional_elo.py
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ingest import SupabaseClient

K_FACTOR = 30
DEFAULT_RATING = 1500.0
ELO_BASE = 2
ELO_DIVISOR = 200
GLOBAL_REGION_TYPE = "global"
GLOBAL_REGION_KEY = "ALL"
STATE_REGION_TYPE = "state"
COMMANDER_PRIMARY_LOOKBACK_MONTHS = 6
COMMANDER_FALLBACK_LOOKBACK_MONTHS = 12
COMMANDER_MIN_PRIMARY_ENTRIES = 2
COMMANDER_RECENCY_HALF_LIFE_DAYS = 15
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


def fetch_null_state_game_rows(client: SupabaseClient) -> List[Dict[str, Any]]:
    """Backfill no-state games until the deployed source view includes them."""
    games = fetch_all(
        client,
        "games",
        [
            (
                "select",
                "id,tournament_id,is_draw,table_number,tournaments!inner(start_date,state,country)",
            ),
            ("tournaments.state", "is.null"),
            ("order", "id.asc"),
        ],
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


def fetch_elo_game_rows(client: SupabaseClient) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_month = next_month(current_month)

    for start in month_starts(2022, end_month.year):
        if start >= end_month:
            break
        end = next_month(start)
        page = fetch_all(
            client,
            "global_elo_game_results",
            [
                (
                    "select",
                    "game_id,tournament_id,entry_id,player_id,start_date,state,country,result,is_draw,table_number",
                ),
                ("order", "start_date.asc,game_id.asc,table_number.asc"),
                ("start_date", f"gte.{start.date().isoformat()}"),
                ("start_date", f"lt.{end.date().isoformat()}"),
            ],
            limit=250,
        )
        rows.extend(page)
        print(f"Fetched {len(page)} game-result rows for {start:%Y-%m}", flush=True)

    raw_null_state_rows = fetch_null_state_game_rows(client)
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
    age_days = (datetime.utcnow().date() - parsed_game_date).days if parsed_game_date else None
    state_key = normalized_state(rows[0])
    country_key = normalized_country(rows[0])

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
    updated_at = datetime.utcnow().isoformat()
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


def compute_global_elo() -> tuple[Dict[str, PlayerStats], Dict[str, Dict[str, StateActivity]], List[Dict[str, Any]]]:
    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    rows = fetch_elo_game_rows(client)

    global_stats: Dict[str, PlayerStats] = defaultdict(PlayerStats)
    state_activity: Dict[str, Dict[str, StateActivity]] = defaultdict(lambda: defaultdict(StateActivity))
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
            process_game(buffer, global_stats, state_activity, event_rows, current_game_date)
            buffer = []
            current_game_id = game_id
            current_game_date = row.get("start_date")

        buffer.append(row)

    if buffer:
        process_game(buffer, global_stats, state_activity, event_rows, current_game_date)

    for player_states in state_activity.values():
        primary_state: str | None = None
        primary_sort_key: tuple[float, str, int, int, str] | None = None
        for region_key, activity in player_states.items():
            activity.activity_score = bucketed_activity_score(activity)
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

    return global_stats, state_activity, event_rows


def build_state_activity_rows(state_activity: Dict[str, Dict[str, StateActivity]]) -> List[Dict[str, Any]]:
    updated_at = datetime.utcnow().isoformat()
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


def fetch_commander_usage_rows(client: SupabaseClient) -> Dict[str, List[CommanderUsage]]:
    rows = fetch_all(
        client,
        "player_commander_entries",
        [
            (
                "select",
                "player_id,topdeck_id,player_name,commander_name,start_date",
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
            )
        )

    print(f"Fetched commander history for {len(by_topdeck_id)} players", flush=True)
    return by_topdeck_id


def delete_optional_rows(client: SupabaseClient, table: str, filters: Dict[str, Any]) -> None:
    try:
        client.delete(table, filters)
    except Exception as exc:
        print(
            f"Skipping delete for {table}; upsert will replace matching rows. Error: {exc}",
            flush=True,
        )


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
    updated_at = datetime.utcnow().isoformat()
    reference = datetime.utcnow().date()
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


def upsert_state_activity_rows(client: SupabaseClient, rows: List[Dict[str, Any]]) -> None:
    try:
        upsert_rows(
            client,
            "global_elo_state_activity",
            rows,
            on_conflict="region_type,region_key,player_id",
        )
    except Exception as exc:
        print(
            "Falling back to global_elo_state_activity without country_key. "
            f"Apply the country-region migration to store country_key. Error: {exc}",
            flush=True,
        )
        fallback_rows = [{key: value for key, value in row.items() if key != "country_key"} for row in rows]
        upsert_rows(
            client,
            "global_elo_state_activity",
            fallback_rows,
            on_conflict="region_type,region_key,player_id",
        )


def main() -> None:
    supabase_url, supabase_key = load_credentials()
    client = SupabaseClient(supabase_url, supabase_key)

    global_stats, state_activity, event_rows = compute_global_elo()
    event_rows = dedupe_rows(event_rows, ["region_type", "region_key", "game_id", "player_id"])
    rating_rows = build_upsert_rows(GLOBAL_REGION_TYPE, GLOBAL_REGION_KEY, global_stats)
    state_activity_rows = build_state_activity_rows(state_activity)
    commander_profile_rows = build_commander_profile_rows(client)

    if not rating_rows:
        raise SystemExit("Refusing to clear Regional Elo rows because no global rating rows were computed.")

    print("Deleting existing global Elo, state activity, and event rows")
    client.delete("global_elo_ratings", {"region_type": f"eq.{GLOBAL_REGION_TYPE}"})
    client.delete("global_elo_state_activity", {"region_type": f"eq.{STATE_REGION_TYPE}"})
    delete_optional_rows(client, "global_elo_game_events", {"region_type": f"eq.{GLOBAL_REGION_TYPE}"})

    upsert_rows(
        client,
        "global_elo_ratings",
        rating_rows,
        on_conflict="region_type,region_key,player_id",
    )
    upsert_state_activity_rows(client, state_activity_rows)
    upsert_rows(
        client,
        "global_elo_game_events",
        event_rows,
        on_conflict="region_type,region_key,game_id,player_id",
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
