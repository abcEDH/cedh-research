"""
Pilot-skill confound analysis (v2).

Question: Gemini's "Turbo decks punch up in large events" finding shows
RogSi etc. hit ~2x expected Top-16 conversion in Large/Major events.
Is that a deck-intrinsic effect, or are these commanders selected by
stronger pilots who would have converted regardless of choice?

Skill proxy: our internal global Elo (`global_elo_ratings`, region=ALL).
88k players covered vs ~10k in TopDeck's separate ranking.

Endogeneity caveat: current Elo includes results from the entries we're
analyzing, so a Turbo pilot who Top-16'd has inflated current Elo. This
means stratifying by current Elo is *over-controlling* — we're partly
conditioning on the outcome variable. The bias works against finding a
residual deck effect, so any positive Elo-adjusted Turbo lift is a
conservative lower bound on the true deck-level effect.

Decomposition:
  1. Are Turbo entries piloted by systematically higher-Elo players?
  2. Does the T16-conversion advantage survive when stratifying by
     pilot Elo quartile?
  3. Compare naive Turbo T16 lift vs Elo-adjusted lift (direct
     standardization) on the Large+Major subset.
"""

import os
import sys
from collections import defaultdict
from statistics import mean, median

import requests


URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}

PAGE = 1000

TURBO_COMMANDERS = {
    "cd977a8e-7f3c-460b-b055-d73f997122f2": "Etali, Primal Conqueror",
    "04e13342-b734-4cd8-8f1c-7ba8199226a0": "RogSi",
    "45b0721d-7dc8-415f-b878-3b3059920dfe": "DargoTymna",
    "d943d7db-2fe7-4662-b4e1-220afda88991": "Ral, Monsoon Mage",
    "2c2235d2-4de9-459e-ba87-06a3be818840": "Inalla",
    "956d2fbb-fec5-42bc-bb47-50583d57b481": "K'rrik",
}

BUCKETS = [
    ("Locals (<32)",  0,   31),
    ("Mid (32-63)",   32,  63),
    ("Large (64-127)", 64, 127),
    ("Major (128+)",  128, 99999),
]


def bucket_for(player_count: int | None) -> str | None:
    if player_count is None:
        return None
    for name, lo, hi in BUCKETS:
        if lo <= player_count <= hi:
            return name
    return None


def fetch_all(path: str, select: str) -> list[dict]:
    out: list[dict] = []
    offset = 0
    sep = "&" if "?" in path else "?"
    while True:
        url = f"{URL}/rest/v1/{path}{sep}select={select}&limit={PAGE}&offset={offset}"
        r = requests.get(url, headers=H, timeout=180)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
        if offset % 20_000 == 0:
            print(f"  ... {len(out):>8} rows from {path[:55]}", file=sys.stderr, flush=True)
    return out


def quartile_label(elo: float, breaks: list[float]) -> str:
    if elo < breaks[0]:
        return "Q1 (low)"
    if elo < breaks[1]:
        return "Q2"
    if elo < breaks[2]:
        return "Q3"
    return "Q4 (high)"


def main() -> None:
    print("Loading global Elo ratings (skill proxy)...", file=sys.stderr, flush=True)
    ratings = fetch_all(
        "global_elo_ratings?region_type=eq.global&region_key=eq.ALL",
        "player_id,rating,games_played",
    )
    elo_by_pid = {r["player_id"]: {"elo": r["rating"], "games_played": r["games_played"]}
                  for r in ratings if r["rating"] is not None}
    print(f"  {len(elo_by_pid):,} players with global Elo", file=sys.stderr, flush=True)

    print("Loading tournament entries...", file=sys.stderr, flush=True)
    entries = fetch_all(
        "tournament_entries",
        "player_id,commander_id,made_top_16,tournaments(player_count)",
    )
    print(f"  {len(entries):,} entries", file=sys.stderr, flush=True)

    rows: list[dict] = []
    skipped_no_pid = skipped_no_elo = skipped_no_bucket = 0
    for e in entries:
        pid = e.get("player_id")
        if not pid:
            skipped_no_pid += 1
            continue
        elo_rec = elo_by_pid.get(pid)
        if not elo_rec:
            skipped_no_elo += 1
            continue
        t = e.get("tournaments") or {}
        bucket = bucket_for(t.get("player_count"))
        if bucket is None:
            skipped_no_bucket += 1
            continue
        rows.append({
            "cid": e.get("commander_id"),
            "is_turbo": e.get("commander_id") in TURBO_COMMANDERS,
            "bucket": bucket,
            "pilot_elo": float(elo_rec["elo"]),
            "pilot_games": elo_rec.get("games_played") or 0,
            "t16": bool(e.get("made_top_16")),
        })

    print(f"  classifiable: {len(rows):,} | "
          f"skip(no_pid)={skipped_no_pid:,} skip(no_elo)={skipped_no_elo:,} "
          f"skip(no_bucket)={skipped_no_bucket:,}")

    n_turbo = sum(1 for r in rows if r["is_turbo"])
    print(f"  Turbo: {n_turbo:,} | Rest: {len(rows) - n_turbo:,}")

    # === Q1: pilot Elo by cohort × bucket ===
    print("\n=== Q1: Pilot TopDeck Elo by cohort × tournament size ===")
    print(f"{'Bucket':<16} {'Cohort':<6} {'N':>7} "
          f"{'mean':>7} {'median':>7} {'P75':>6} {'P90':>6}")
    for bname, _, _ in BUCKETS:
        for cohort, want in [("Turbo", True), ("Rest", False)]:
            elos = sorted(r["pilot_elo"] for r in rows if r["bucket"] == bname and r["is_turbo"] is want)
            if not elos:
                continue
            n = len(elos)
            p75 = elos[min(n - 1, int(n * 0.75))]
            p90 = elos[min(n - 1, int(n * 0.9))]
            print(f"{bname:<16} {cohort:<6} {n:>7} "
                  f"{mean(elos):>7.0f} {median(elos):>7.0f} {p75:>6.0f} {p90:>6.0f}")

    # === Q2: T16 stratified by pilot Elo quartile ===
    # Quartile breaks taken over Large+Major only so the comparison cohort matches the
    # population where Gemini's finding lives.
    big_rows = [r for r in rows if r["bucket"] in ("Large (64-127)", "Major (128+)")]
    if not big_rows:
        print("\nNo Large/Major rows — abort.", file=sys.stderr)
        return
    elos_big = sorted(r["pilot_elo"] for r in big_rows)
    n = len(elos_big)
    breaks = [elos_big[int(n * q)] for q in (0.25, 0.5, 0.75)]
    print(f"\nLarge+Major Elo quartile breaks (N={n:,}): "
          f"Q1<{breaks[0]:.0f} | Q2<{breaks[1]:.0f} | Q3<{breaks[2]:.0f} | Q4>={breaks[2]:.0f}")

    cell: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for r in big_rows:
        q = quartile_label(r["pilot_elo"], breaks)
        c = "Turbo" if r["is_turbo"] else "Rest"
        cell[(r["bucket"], q, c)][0] += 1
        if r["t16"]:
            cell[(r["bucket"], q, c)][1] += 1

    print("\n=== Q2: Top-16 rate, Large+Major, stratified by pilot Elo quartile ===")
    print(f"{'Bucket':<16} {'Elo Q':<10} "
          f"{'Turbo n':>7} {'Turbo T16%':>11} "
          f"{'Rest n':>7} {'Rest T16%':>10} "
          f"{'lift':>9}")
    for bname in ("Large (64-127)", "Major (128+)"):
        for q in ("Q1 (low)", "Q2", "Q3", "Q4 (high)"):
            tn, tt = cell.get((bname, q, "Turbo"), [0, 0])
            rn, rt = cell.get((bname, q, "Rest"), [0, 0])
            if tn + rn == 0:
                continue
            tr = tt / tn if tn else float("nan")
            rr = rt / rn if rn else float("nan")
            if tn < 10 or rn < 10:
                marker = "*"  # underpowered cell
            else:
                marker = " "
            lift = tr - rr if tn and rn else float("nan")
            print(f"{bname:<16} {q:<10} "
                  f"{tn:>7} {tr*100:>10.1f}% "
                  f"{rn:>7} {rr*100:>9.1f}% "
                  f"{lift*100:>+8.1f}pp{marker}")
    print("*  cell has <10 entries in one cohort — read with caution")

    # === Q3: naive vs Elo-adjusted Turbo T16 lift (Large+Major) ===
    print("\n=== Q3: Naive vs Elo-adjusted Turbo T16 lift (Large+Major pooled) ===")
    t_big = [r for r in big_rows if r["is_turbo"]]
    r_big = [r for r in big_rows if not r["is_turbo"]]
    if not t_big or not r_big:
        print("  cohorts empty")
        return
    naive_t = mean(r["t16"] for r in t_big)
    naive_r = mean(r["t16"] for r in r_big)
    naive_lift = (naive_t - naive_r) * 100
    print(f"  Naive Turbo T16: {naive_t*100:.2f}% (n={len(t_big):,})")
    print(f"  Naive Rest  T16: {naive_r*100:.2f}% (n={len(r_big):,})")
    print(f"  Naive lift:      {naive_lift:+.2f}pp")

    # Direct standardization: weight by Rest's Elo distribution
    # (counterfactual: how would Turbo's T16 rate look if Turbo pilots had Rest's Elo mix?)
    adj_t = 0.0
    total = 0
    for q in ("Q1 (low)", "Q2", "Q3", "Q4 (high)"):
        # Rest weight in this quartile across Large+Major
        rn_q = sum(cell[(b, q, "Rest")][0] for b in ("Large (64-127)", "Major (128+)"))
        # Turbo rate in this quartile across Large+Major
        tn_q = sum(cell[(b, q, "Turbo")][0] for b in ("Large (64-127)", "Major (128+)"))
        tt_q = sum(cell[(b, q, "Turbo")][1] for b in ("Large (64-127)", "Major (128+)"))
        if tn_q == 0:
            continue
        adj_t += (tt_q / tn_q) * rn_q
        total += rn_q
    if total:
        adj_t /= total
        adj_lift = (adj_t - naive_r) * 100
        print(f"  Elo-adjusted Turbo T16 (Rest-weighted): {adj_t*100:.2f}%")
        print(f"  Elo-adjusted lift:                       {adj_lift:+.2f}pp")
        explained = (naive_lift - adj_lift) / naive_lift * 100 if naive_lift else 0
        print(f"  → pilot-Elo selection explains {explained:+.1f}% of the naive Turbo lift")


if __name__ == "__main__":
    main()
