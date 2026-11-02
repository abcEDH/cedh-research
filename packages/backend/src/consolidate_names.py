#!/usr/bin/env python3
"""Apply the canonical-name migration and rebuild affected read models atomically.

Default: read-only audit. --rehearse runs the full transaction then rolls it back.
--apply commits only after conservation checks pass. Does not recompute Elo.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, RealDictCursor, execute_values

from ingest import COMMANDER_NAME_ALIASES, load_local_env, normalize_commander_name
from name_normalization import COUNTRY_ALIASES, REGIONS, canonical_region_name
from rebuild_player_commander_profiles import build_profile_rows, normalize_usage_rows
from tournament_location_corrections import apply_reviewed_corrections

MIGRATION = (
    Path(__file__).resolve().parents[1] / "supabase/migrations/20260918170000_canonical_region_and_commander_names.sql"
)
VERSION = "20260918170000"


def upsert(cursor, table, rows, keys):
    if not rows:
        return
    columns = list(rows[0])
    query = sql.SQL("INSERT INTO public.{} ({}) VALUES %s ON CONFLICT ({}) DO UPDATE SET {}").format(
        sql.Identifier(table),
        sql.SQL(",").join(map(sql.Identifier, columns)),
        sql.SQL(",").join(map(sql.Identifier, keys)),
        sql.SQL(",").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in columns if c not in keys
        ),
    )
    values = [[Json(row[c]) if isinstance(row[c], (dict, list)) else row[c] for c in columns] for row in rows]
    execute_values(cursor, query, values, page_size=2000)


def regional_rows(global_rows, activities):
    """Re-slice existing global rows, retaining all ratings and global counters."""
    primary = {r["player_id"]: r for r in activities if r["is_primary_state"]}
    groups = defaultdict(list)
    for original in global_rows:
        row = dict(original)
        home = primary.get(row["player_id"], {})
        row.update(
            primary_region_key=home.get("region_key"),
            primary_country_key=home.get("country_key"),
            activity_score=home.get("activity_score"),
        )
        groups[("global", "ALL", None)].append(row)
        if home.get("country_key"):
            groups[("country", home["country_key"], home["country_key"])].append(dict(row))
        if home.get("region_key"):
            groups[("state", home["region_key"], home.get("country_key"))].append(dict(row))
    result = []
    for (kind, region, country), rows in groups.items():
        if kind != "global":
            rows.sort(
                key=lambda r: (
                    -float(r["rating"]),
                    -float(r.get("activity_score") or 0),
                    -r["games_played"],
                    r["player_name"],
                )
            )
            for rank, row in enumerate(rows, 1):
                row["rank"] = rank
            rows.sort(key=lambda r: (-float(r.get("topdeck_elo") or 0), -float(r["rating"]), r["player_name"]))
            for rank, row in enumerate(rows, 1):
                row["topdeck_elo_rank"] = rank if row.get("topdeck_elo") is not None else None
        for row in rows:
            row.update(region_type=kind, region_key=region, country_key=country)
            result.append(row)
    return result


def audit(cursor):
    cursor.execute("SELECT version,name FROM supabase_migrations.schema_migrations ORDER BY version DESC LIMIT 3")
    print("Latest migrations:", [dict(r) for r in cursor.fetchall()], flush=True)
    cursor.execute("SELECT state, country, count(*) AS events FROM tournaments GROUP BY state,country")
    changed, unresolved = [], []
    for row in cursor.fetchall():
        target = canonical_region_name(row["state"], row["country"])
        if target != row["state"]:
            changed.append({**dict(row), "canonical": target})
        elif row["state"] and re.fullmatch(r"[A-Z.]{1,3}", row["state"].strip()):
            unresolved.append(dict(row))
    cursor.execute(
        "SELECT c.id,c.name,c.commander_names,count(te.id) AS entries FROM commanders c LEFT JOIN "
        "tournament_entries te ON te.commander_id=c.id GROUP BY c.id"
    )
    commanders = [dict(r) for r in cursor.fetchall()]
    changes = []
    for row in commanders:
        components = row["commander_names"] or row["name"].split(" / ")
        if any(n in COMMANDER_NAME_ALIASES for n in [*components, *row["name"].split(" / ")]):
            changes.append(
                {"name": row["name"], "canonical": normalize_commander_name(components), "entries": row["entries"]}
            )
    display_changes = [
        {"current": r["name"], "proposed": normalize_commander_name(r["commander_names"]), "entries": r["entries"]}
        for r in commanders
        if normalize_commander_name(r["commander_names"]) != r["name"]
    ]
    print(
        json.dumps(
            {
                "region_events_to_normalize": sum(r["events"] for r in changed),
                "unresolved_short_regions": unresolved,
                "commanders_audited": len(commanders),
                "commander_alias_rows": changes,
                "commander_display_changes": display_changes,
            },
            default=str,
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )


def snapshot(cursor):
    # Compact checksums prove ratings/events and base fact counts are unchanged.
    cursor.execute("""SELECT
      (SELECT count(*) FROM tournament_entries) AS entries,
      (SELECT count(*) FROM commander_matchups) AS matchups,
      (SELECT md5(string_agg(md5(row_to_json(r)::text), '' ORDER BY id)) FROM global_elo_ratings r) AS ratings,
      (SELECT count(*) FROM global_elo_game_events) AS game_events""")
    return dict(cursor.fetchone())


def rebuild(cursor, affected_player_ids):
    cursor.execute("SELECT * FROM global_elo_active_leaderboard WHERE region_type='global' AND region_key='ALL'")
    global_rows = [dict(r) for r in cursor.fetchall()]
    # Derive regional counts from canonical facts; never add overlapping summaries.
    cursor.execute("""WITH grouped AS (
      SELECT e.player_id, upper(btrim(t.state)) AS region_key,
        nullif(upper(btrim(t.country)), '') AS country_key,
        count(*)::int AS games_lifetime,
        count(*) FILTER (WHERE e.game_result='win')::int AS wins,
        count(*) FILTER (WHERE e.game_result='draw')::int AS draws,
        count(*) FILTER (WHERE e.game_result='loss')::int AS losses,
        count(*) FILTER (WHERE e.game_date::date >= current_date-30)::int AS games_30d,
        count(*) FILTER (WHERE e.game_date::date >= current_date-90)::int AS games_90d,
        count(*) FILTER (WHERE e.game_date::date >= current_date-365)::int AS games_365d,
        max(e.game_date)::date AS last_game_date,
        round(sum(power(0.5::numeric, greatest(current_date-e.game_date::date,0)::numeric/180)),6) AS activity_score
      FROM global_elo_game_events e JOIN tournaments t ON t.id=e.tournament_id
      WHERE e.region_type='global' AND e.region_key='ALL' AND nullif(btrim(t.state),'') IS NOT NULL
      GROUP BY e.player_id, upper(btrim(t.state)), upper(btrim(t.country))
    ), combined AS (
      SELECT player_id, region_key, min(country_key) AS country_key,
        sum(games_lifetime)::int AS games_lifetime, sum(wins)::int AS wins,
        sum(draws)::int AS draws, sum(losses)::int AS losses,
        sum(games_30d)::int AS games_30d, sum(games_90d)::int AS games_90d,
        sum(games_365d)::int AS games_365d, max(last_game_date) AS last_game_date,
        sum(activity_score) AS activity_score
      FROM grouped GROUP BY player_id,region_key
    ) SELECT *, 'state' AS region_type,
      row_number() OVER (PARTITION BY player_id ORDER BY activity_score DESC,games_lifetime DESC,
        last_game_date DESC,region_key DESC)=1 AS is_primary_state
      FROM combined""")
    activities = [dict(r) for r in cursor.fetchall()]
    print(f"Computed {len(activities)} regional activity rows", flush=True)
    # Preserve country inference for international names outside the alias catalog.
    from rebuild_global_elo_tables import infer_country

    for row in activities:
        if not row["country_key"]:
            candidates = {r["country"] for r in REGIONS if r["name"].upper() == row["region_key"]}
            row["country_key"] = (
                next(iter(candidates)) if len(candidates) == 1 else infer_country(row["region_key"], None) or None
            )
        row["country_key"] = COUNTRY_ALIASES.get(row["country_key"], row["country_key"])
    cursor.execute("DELETE FROM global_elo_state_activity WHERE region_type='state'")
    upsert(cursor, "global_elo_state_activity", activities, ["region_type", "region_key", "player_id"])
    leaderboard = regional_rows(global_rows, activities)
    cursor.execute("DELETE FROM global_elo_active_leaderboard")
    upsert(cursor, "global_elo_active_leaderboard", leaderboard, ["region_type", "region_key", "player_id"])
    cursor.execute("""WITH grouped AS (
      SELECT player_id,
        max(region_key) FILTER (WHERE is_primary_state) AS home_region,
        max(country_key) FILTER (WHERE is_primary_state) AS home_country,
        jsonb_agg(jsonb_build_object('country_key',country_key,'region_key',region_key,
          'games_played',games_lifetime,'wins',wins,'draws',draws,'losses',losses)
          ORDER BY activity_score DESC,games_lifetime DESC,region_key) AS assignments
      FROM global_elo_state_activity GROUP BY player_id
    ) UPDATE global_elo_player_profile_summaries p SET
      home_region_key=a.home_region,home_country_key=a.home_country,
      state_assignments=a.assignments,updated_at=now()
      FROM grouped a WHERE p.player_id=a.player_id""")
    cursor.execute("""UPDATE global_elo_player_profile_summaries p SET
      home_region_key=NULL,home_country_key=NULL,state_assignments='[]'::jsonb,updated_at=now()
      WHERE (home_region_key IS NOT NULL OR home_country_key IS NOT NULL OR state_assignments<>'[]'::jsonb)
        AND NOT EXISTS (SELECT 1 FROM global_elo_state_activity a WHERE a.player_id=p.player_id)""")
    cursor.execute(
        """SELECT te.player_id,te.decklist_url,p.topdeck_id,p.name AS player_name,
      c.name AS commander_name,t.id AS tournament_id,t.name AS tournament_name,t.start_date,t.topdeck_tid
      FROM tournament_entries te JOIN players p ON p.id=te.player_id
      JOIN commanders c ON c.id=te.commander_id JOIN tournaments t ON t.id=te.tournament_id
      WHERE p.topdeck_id IS NOT NULL AND te.player_id=ANY(%s::uuid[])""",
        (affected_player_ids,),
    )
    print("Rebuilding commander predictions", flush=True)
    profiles = build_profile_rows(
        normalize_usage_rows([dict(r) for r in cursor.fetchall()], datetime.now(UTC).date()), datetime.now(UTC).date()
    )
    upsert(cursor, "player_commander_profiles", profiles, ["player_id"])
    cursor.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND "
        "table_name='global_elo_player_profile_summaries' AND column_name='primary_commander_name'"
    )
    if cursor.fetchone():
        cursor.execute("""UPDATE global_elo_player_profile_summaries p SET primary_commander_name=coalesce(
          (SELECT c.name FROM commanders c WHERE
            c.commander_names @> public.canonical_commander_components(string_to_array(p.primary_commander_name,' / '))
            AND c.commander_names <@ public.canonical_commander_components(
              string_to_array(p.primary_commander_name,' / '))
            ORDER BY c.name LIMIT 1),
          array_to_string(
            public.canonical_commander_components(string_to_array(p.primary_commander_name,' / ')),' / '))
          WHERE p.primary_commander_name IS DISTINCT FROM array_to_string(
            public.canonical_commander_components(string_to_array(p.primary_commander_name,' / ')),' / ')""")
    # Refresh only materializations downstream of changed identities/locations.
    # Include indirect dependencies so downstream summaries stay consistent.
    cursor.execute("""WITH RECURSIVE deps AS (
      SELECT DISTINCT c.oid,c.relname,0 AS depth
      FROM pg_depend dep JOIN pg_rewrite rw ON rw.oid=dep.objid
      JOIN pg_class c ON c.oid=rw.ev_class
      WHERE c.relkind IN ('v','m') AND (
        dep.refobjid='public.commanders'::regclass
        OR (dep.refobjid='public.tournaments'::regclass AND dep.refobjsubid IN
            (SELECT attnum FROM pg_attribute WHERE attrelid='public.tournaments'::regclass
              AND attname IN ('state','country')))
        OR (dep.refobjid='public.tournament_entries'::regclass AND dep.refobjsubid=
            (SELECT attnum FROM pg_attribute WHERE attrelid='public.tournament_entries'::regclass
              AND attname='commander_id'))
      )
      UNION
      SELECT v.oid,v.relname,d.depth+1 FROM deps d
      JOIN pg_depend dep ON dep.refobjid=d.oid
      JOIN pg_rewrite rw ON rw.oid=dep.objid JOIN pg_class v ON v.oid=rw.ev_class
      WHERE v.relkind IN ('v','m') AND v.oid<>d.oid AND d.depth<20
    ) SELECT relname FROM deps WHERE oid IN (SELECT oid FROM pg_class WHERE relkind='m')
      GROUP BY relname ORDER BY max(depth),relname""")
    views = [row["relname"] for row in cursor.fetchall()]
    # Parsing every historical decklist is an existing, expensive maintenance
    # operation; do not change its analytics logic to speed up this backfill.
    cursor.execute("SET LOCAL statement_timeout='900s'")
    for view in views:
        print(f"Refreshing {view}", flush=True)
        cursor.execute(sql.SQL("REFRESH MATERIALIZED VIEW public.{}").format(sql.Identifier(view)))
    cursor.execute("SET LOCAL statement_timeout='180s'")
    print(
        f"Rebuilt {len(activities)} regional rows, {len(leaderboard)} leaderboard rows, "
        f"{len(profiles)} commander profiles",
        flush=True,
    )


def validate_database_aliases(cursor):
    for region in REGIONS:
        for alias in [region["name"], *region["aliases"]]:
            cursor.execute("SELECT public.canonical_region_name(%s,%s) AS name", (alias, region["country"]))
            if cursor.fetchone()["name"] != region["name"]:
                raise RuntimeError(f"Database/Python alias mismatch: {alias}")
    for state, country in [
        ("WA", None),
        ("WA", "US"),
        ("WA", "AU"),
        ("BC", "US"),
        ("CA", None),
        ("undefined", None),
        ("Baja California", None),
    ]:
        cursor.execute("SELECT public.canonical_region_name(%s,%s) AS name", (state, country))
        if cursor.fetchone()["name"] != canonical_region_name(state, country):
            raise RuntimeError(f"Database/Python ambiguity mismatch: {state}")
    cursor.execute(
        "SELECT alias FROM commander_name_aliases WHERE "
        "public.canonical_commander_components(ARRAY[alias]) <> ARRAY[canonical_name]"
    )
    if cursor.fetchall():
        raise RuntimeError("Commander database catalog resolution failed")
    cursor.execute("SAVEPOINT alias_write_check")
    cursor.execute(
        "INSERT INTO commanders(name,commander_names) VALUES ('Kavaero, "
        "Mind-Bitten',ARRAY['Kavaero, Mind-Bitten']) ON CONFLICT(name) DO UPDATE SET "
        "commander_names=excluded.commander_names RETURNING name,commander_names"
    )
    row = cursor.fetchone()
    if row["name"] != "Superior Spider-Man" or row["commander_names"] != ["Superior Spider-Man"]:
        raise RuntimeError("Commander alias trigger failed")
    cursor.execute(
        "INSERT INTO commanders(name,commander_names) VALUES ('Cecil Harvey / Hugo "
        "Kupka',ARRAY['Cecil Harvey','Hugo Kupka']) ON CONFLICT(name) DO UPDATE SET "
        "commander_names=excluded.commander_names RETURNING name,commander_names"
    )
    row = cursor.fetchone()
    if row["commander_names"] != normalize_commander_name(["Cecil Harvey", "Hugo Kupka"]).split(" / "):
        raise RuntimeError("Partner alias trigger failed")
    cursor.execute(
        "INSERT INTO commanders(name,commander_names) VALUES ('Esika, God of the Tree // The "
        "Prismatic Bridge',ARRAY['Esika, God of the Tree // The Prismatic Bridge']) ON "
        "CONFLICT(name) DO UPDATE SET commander_names=excluded.commander_names RETURNING "
        "name,commander_names"
    )
    row = cursor.fetchone()
    if row["name"] != "Esika, God of the Tree" or row["commander_names"] != ["Esika, God of the Tree"]:
        raise RuntimeError("Double-faced front-name normalization failed")
    for name in ["SP//dr, Piloted by Peni", "Kraum, Ludevic’s Opus", "K\\'rrik, Son of Yawgmoth"]:
        cursor.execute("SELECT public.canonical_commander_components(ARRAY[%s]) AS names", (name,))
        if cursor.fetchone()["names"] != normalize_commander_name([name]).split(" / "):
            raise RuntimeError(f"Commander punctuation mismatch: {name}")
    cursor.execute("SELECT pair_key,commander_names FROM commander_pair_display_order")
    for row in cursor.fetchall():
        if normalize_commander_name(row["commander_names"]).split(" / ") != row["commander_names"]:
            raise RuntimeError(f"Saved partner order mismatch: {row['pair_key']}")
    cursor.execute("ROLLBACK TO SAVEPOINT alias_write_check")
    cursor.execute("RELEASE SAVEPOINT alias_write_check")
    print("Database alias and future-write checks passed", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rehearse", action="store_true")
    args = parser.parse_args()
    load_local_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=15)
    try:
        conn.set_session(readonly=not (args.apply or args.rehearse))
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SET statement_timeout='180s'")
            cursor.execute("SET lock_timeout='10s'")
            audit(cursor)
            if not (args.apply or args.rehearse):
                return
            # Prevent facts changing while names and derived snapshots are rebuilt.
            cursor.execute(
                "LOCK TABLE "
                "tournaments,commanders,tournament_entries,commander_matchups,global_elo_ratings,global_elo"
                "_game_events,global_elo_state_activity,global_elo_active_leaderboard,global_elo_player_pro"
                "file_summaries,player_commander_profiles IN SHARE ROW EXCLUSIVE MODE"
            )
            cursor.execute("SELECT id,name,commander_names FROM commanders")
            affected_commanders = [
                r["id"]
                for r in cursor.fetchall()
                if normalize_commander_name(r["commander_names"]) != r["name"]
                or normalize_commander_name(r["commander_names"]).split(" / ") != r["commander_names"]
            ]
            cursor.execute(
                "SELECT DISTINCT player_id FROM tournament_entries WHERE commander_id=ANY(%s::uuid[])",
                (affected_commanders,),
            )
            affected_player_ids = [r["player_id"] for r in cursor.fetchall()]
            print(f"Rebuilding commander predictions for {len(affected_player_ids)} affected players", flush=True)
            before = snapshot(cursor)
            repaired = apply_reviewed_corrections(cursor)
            print(f"Applied {repaired} reviewed event location corrections", flush=True)
            cursor.execute("SELECT name FROM supabase_migrations.schema_migrations WHERE version=%s", (VERSION,))
            existing = cursor.fetchone()
            if existing and existing["name"] != "canonical_region_and_commander_names":
                raise RuntimeError("Migration version already belongs to another change")
            if not existing:
                cursor.execute(MIGRATION.read_text())
                cursor.execute(
                    "INSERT INTO supabase_migrations.schema_migrations(version,name,statements) VALUES (%s,%s,%s)",
                    (VERSION, "canonical_region_and_commander_names", [MIGRATION.read_text()]),
                )
            validate_database_aliases(cursor)
            rebuild(cursor, affected_player_ids)
            if snapshot(cursor) != before:
                raise RuntimeError("Conservation check failed; rolling back")
            cursor.execute(
                "SELECT c.name FROM commanders c JOIN commander_name_aliases a ON a.alias=ANY(c.commander_names)"
            )
            if cursor.fetchall():
                raise RuntimeError("Unmerged commander aliases remain")
            cursor.execute("SELECT name FROM commanders WHERE name LIKE '%% // %%'")
            if cursor.fetchall():
                raise RuntimeError("Back-face names remain in commander display names")
            audit(cursor)
        if args.apply:
            conn.commit()
            print("Committed. Ratings and fact counts unchanged.", flush=True)
        else:
            conn.rollback()
            print("Rehearsal passed; all changes rolled back.", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
