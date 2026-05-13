import os
import requests
from collections import defaultdict
from datetime import datetime

def analyze_ban_impact():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    ban_date = "2024-09-23"
    
    print("Fetching tournament entries summary...")
    # Since we have 272k entries, we will fetch in larger batches
    # and only what we need.
    
    periods = {
        "Pre-Ban": {"win_rate": 0.0, "made_top_16": 0, "draws": 0, "wins": 0, "losses": 0, "entries": 0},
        "Post-Ban": {"win_rate": 0.0, "made_top_16": 0, "draws": 0, "wins": 0, "losses": 0, "entries": 0}
    }

    limit = 10000
    offset = 0
    while True:
        query_url = f"{url}/rest/v1/tournament_entries?select=win_rate,draws,wins,losses,made_top_16,tournaments(start_date)&limit={limit}&offset={offset}"
        response = requests.get(query_url, headers=headers)
        batch = response.json()
        if not batch or len(batch) == 0: break
        
        for entry in batch:
            if not entry.get("tournaments"): continue
            start_date = entry["tournaments"]["start_date"]
            if not start_date: continue
            
            period = "Pre-Ban" if start_date < ban_date else "Post-Ban"
            p = periods[period]
            p["entries"] += 1
            p["win_rate"] += (entry["win_rate"] or 0)
            p["draws"] += (entry["draws"] or 0)
            p["wins"] += (entry["wins"] or 0)
            p["losses"] += (entry["losses"] or 0)
            if entry["made_top_16"]:
                p["made_top_16"] += 1
        
        offset += limit
        print(f"Processed {offset} entries...")
        if offset > 100000: break # Let's stop at 100k for now to avoid timeout
        if len(batch) < limit: break

    print(f"\n{'Period':<30} | {'Entries':<10} | {'Avg WR':<10} | {'T16 Rate':<10} | {'Draw Rate':<10}")
    print("-" * 85)
    
    for name in ["Pre-Ban", "Post-Ban"]:
        p = periods[name]
        if p["entries"] == 0: continue
        
        avg_wr = p["win_rate"] / p["entries"]
        t16_rate = p["made_top_16"] / p["entries"]
        
        total_games = p["wins"] + p["losses"] + p["draws"]
        draw_rate = p["draws"] / total_games if total_games > 0 else 0
        
        print(f"{name:<30} | {p['entries']:<10} | {avg_wr:>9.1%} | {t16_rate:>9.1%} | {draw_rate:>9.1%}")

    # Seat Position Analysis
    print("\nFetching seat position data...")
    seat_periods = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "total": 0}))
    
    limit = 10000
    offset = 0
    while True:
        g_url = f"{url}/rest/v1/game_participants?select=result,seat_position,games(tournaments(start_date))&limit={limit}&offset={offset}"
        res = requests.get(g_url, headers=headers)
        batch = res.json()
        if not batch or len(batch) == 0: break
        
        for p in batch:
            if not p.get("games") or not p["games"].get("tournaments"): continue
            start_date = p["games"]["tournaments"]["start_date"]
            if not start_date: continue
            
            period = "Pre-Ban" if start_date < ban_date else "Post-Ban"
            seat = (p["seat_position"] or 0) + 1 
            if seat > 4: continue
            
            seat_periods[period][seat]["total"] += 1
            if p["result"] == "win":
                seat_periods[period][seat]["wins"] += 1
        
        offset += limit
        print(f"Processed {offset} game results...")
        if offset > 100000: break
        if len(batch) < limit: break

    print(f"\n{'Period':<30} | {'Seat 1':<8} | {'Seat 2':<8} | {'Seat 3':<8} | {'Seat 4':<8}")
    print("-" * 75)
    for period in ["Pre-Ban", "Post-Ban"]:
        row = f"{period:<30}"
        for seat in range(1, 5):
            stats = seat_periods[period][seat]
            wr = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
            row += f" | {wr:>7.1%}"
        print(row)

if __name__ == "__main__":
    analyze_ban_impact()
