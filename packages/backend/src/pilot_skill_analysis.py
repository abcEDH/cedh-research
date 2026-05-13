import os
import requests
from collections import defaultdict

def analyze_pilot_vs_deck():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # 1. Get Top 500 Pilots by TopDeck Elo
    print("Fetching top 500 elite pilot IDs...")
    elo_url = f"{url}/rest/v1/topdeck_player_elos?order=elo.desc&limit=500"
    elo_res = requests.get(elo_url, headers=headers)
    top_pilots = {p["topdeck_id"]: p["elo"] for p in elo_res.json() if p.get("topdeck_id")}
    
    # 2. Define Deck Map with correct IDs
    commander_map = {
        "04e13342-b734-4cd8-8f1c-7ba8199226a0": "RogSi (Turbo)",
        "386996c0-3916-4ebe-9884-6eec90aa952b": "RogThras (Turbo)",
        "45b0721d-7dc8-415f-b878-3b3059920dfe": "DargoTymna (Turbo)",
        "d943d7db-2fe7-4662-b4e1-220afda88991": "Ral (Turbo)",
        "2c2235d2-4de9-459e-ba87-06a3be818840": "Inalla (Turbo)",
        "956d2fbb-fec5-42bc-bb47-50583d57b481": "Krrik (Turbo)",
        "6739a060-7dcd-4eb9-9890-e2260308b4bb": "Blue Farm (Midrange)",
        "b6afe38f-0101-4fd0-a97a-0326486fe1d8": "Kinnan (Midrange)",
        "84566484-34d8-4050-bb75-35b3ac5326c8": "Sisay (Midrange)",
        "049d06e9-5d7e-4b71-89c4-0cf9521a15da": "TymnaThras (Midrange)"
    }

    # stats[commander][tier] = {wr_total, count, t16s}
    stats = defaultdict(lambda: defaultdict(lambda: {"wr_total": 0.0, "count": 0, "t16s": 0}))

    for cmd_id, cmd_name in commander_map.items():
        print(f"Processing {cmd_name}...")
        offset = 0
        limit = 1000
        while True:
            entries_url = f"{url}/rest/v1/tournament_entries?commander_id=eq.{cmd_id}&select=win_rate,made_top_16,players(topdeck_id),tournaments(player_count)&limit={limit}&offset={offset}"
            entries = requests.get(entries_url, headers=headers).json()
            if not entries or len(entries) == 0: break
            
            for e in entries:
                if not e.get("tournaments") or e["tournaments"]["player_count"] < 32:
                    continue
                
                player_data = e.get("players")
                if not player_data: continue
                
                td_id = player_data.get("topdeck_id")
                tier = "Elite" if td_id in top_pilots else "General"
                
                s = stats[cmd_name][tier]
                s["count"] += 1
                s["wr_total"] += (e["win_rate"] or 0)
                if e["made_top_16"]:
                    s["t16s"] += 1

            offset += limit
            if len(entries) < limit: break

    # 4. Print Comparison Table
    print(f"\n{'Commander Archetype':<25} | {'Tier':<8} | {'N':<6} | {'Win%':>6} | {'T16%':>6} | {'Gap (WR)'} | {'Gap (T16)'}")
    print("-" * 100)
    
    for cmd in sorted(stats.keys()):
        elite = stats[cmd]["Elite"]
        gen = stats[cmd]["General"]
        
        wr_gap = (elite["wr_total"]/elite["count"] - gen["wr_total"]/gen["count"]) if elite["count"] > 0 and gen["count"] > 0 else 0
        t16_gap = (elite["t16s"]/elite["count"] - gen["t16s"]/gen["count"]) if elite["count"] > 0 and gen["count"] > 0 else 0
        elite_share = elite["count"] / (elite["count"] + gen["count"]) if (elite["count"] + gen["count"]) > 0 else 0

        for tier in ["Elite", "General"]:
            s = stats[cmd][tier]
            if s["count"] == 0: continue
            
            wr = s["wr_total"] / s["count"]
            t16 = s["t16s"] / s["count"]
            
            if tier == "Elite":
                print(f"{cmd:<25} | {tier:<8} | {s['count']:<6} | {wr:>6.1%} | {t16:>6.1%} | {wr_gap:>+7.1%} | {t16_gap:>+7.1%}")
            else:
                print(f"{' (Elite Share: '+f'{elite_share:.1%}'+')':<25} | {tier:<8} | {s['count']:<6} | {wr:>6.1%} | {t16:>6.1%} | {'':>7} | {'':>7}")
        print("-" * 100)

if __name__ == "__main__":
    analyze_pilot_vs_deck()
