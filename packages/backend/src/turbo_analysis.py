import os
import requests
import json
from collections import defaultdict

def analyze_turbo_performance():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # Commander IDs from the URLs + Inalla/Krrik for context
    commander_ids = {
        "cd977a8e-7f3c-460b-b055-d73f997122f2": "Etali, Primal Conqueror",
        "04e13342-b734-4cd8-8f1c-7ba8199226a0": "RogSi",
        "45b0721d-7dc8-415f-b878-3b3059920dfe": "DargoTymna",
        "d943d7db-2fe7-4662-b4e1-220afda88991": "Ral, Monsoon Mage",
        "2c2235d2-4de9-459e-ba87-06a3be818840": "Inalla",
        "956d2fbb-fec5-42bc-bb47-50583d57b481": "Krrik"
    }

    all_entries = []
    for cmd_id, cmd_name in commander_ids.items():
        query_url = f"{url}/rest/v1/tournament_entries?commander_id=eq.{cmd_id}&select=commander_id,win_rate,made_top_cut,made_top_16,final_standing,tournaments(player_count)&limit=5000"
        response = requests.get(query_url, headers=headers)
        entries = response.json()
        if isinstance(entries, list):
            all_entries.extend(entries)
            print(f"Found {len(entries)} entries for {cmd_name}")
    
    entries = all_entries
    print(f"Total entries analyzed: {len(entries)}")
    # ... rest of code
    buckets = [
        {"name": "Locals (<32)", "min": 0, "max": 31},
        {"name": "Mid (32-63)", "min": 32, "max": 63},
        {"name": "Large (64-127)", "min": 64, "max": 127},
        {"name": "Major (128+)", "min": 128, "max": 9999}
    ]

    stats = defaultdict(lambda: defaultdict(lambda: {
        "entries": 0,
        "total_wr": 0.0,
        "top_16s": 0,
        "top_cuts": 0
    }))

    for entry in entries:
        cmd_id = entry["commander_id"]
        cmd_name = commander_ids.get(cmd_id, "Unknown")
        player_count = entry["tournaments"]["player_count"] if entry["tournaments"] else 0
        
        # Find bucket
        bucket_name = "Unknown"
        for b in buckets:
            if b["min"] <= player_count <= b["max"]:
                bucket_name = b["name"]
                break
        
        s = stats[cmd_name][bucket_name]
        s["entries"] += 1
        s["total_wr"] += (entry["win_rate"] or 0)
        if entry["made_top_16"]:
            s["top_16s"] += 1
        if entry["made_top_cut"]:
            s["top_cuts"] += 1

    # Print results
    print(f"{'Commander':<30} | {'Bucket':<15} | {'Entries':<7} | {'WR Delta':<8} | {'T16 Rel':<8} | {'TC Rel':<8}")
    print("-" * 95)
    
    for cmd_name in sorted(stats.keys()):
        for bucket in buckets:
            bucket_name = bucket["name"]
            s = stats[cmd_name][bucket_name]
            if s["entries"] == 0:
                continue
            
            avg_wr = s["total_wr"] / s["entries"]
            wr_delta = avg_wr - 0.25
            
            # Estimate expected conversion
            # T16: 16 / avg_players_in_bucket
            # TC: assume 4 for <32, 8 for 32-63, 16 for 64+
            avg_players = (bucket["min"] + bucket["max"]) / 2
            if bucket["max"] > 1000: avg_players = 160 # Major estimate
            
            exp_t16 = min(1.0, 16 / avg_players)
            
            if bucket["max"] < 32: exp_tc = 4 / avg_players
            elif bucket["max"] < 64: exp_tc = 8 / avg_players
            else: exp_tc = 16 / avg_players
            
            t16_conv = s["top_16s"] / s["entries"]
            tc_conv = s["top_cuts"] / s["entries"]
            
            t16_rel = t16_conv / exp_t16 if exp_t16 > 0 else 0
            tc_rel = tc_conv / exp_tc if exp_tc > 0 else 0
            
            print(f"{cmd_name:<30} | {bucket_name:<15} | {s['entries']:<7} | {wr_delta:>+7.1%} | {t16_rel:>7.1}x | {tc_rel:>7.1}x")
        print("-" * 95)

if __name__ == "__main__":
    analyze_turbo_performance()
