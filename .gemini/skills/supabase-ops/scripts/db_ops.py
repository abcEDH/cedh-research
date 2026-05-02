import os
import requests
import json
import argparse
import sys

def get_config():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    return url, key

def rpc(url, key, function, params):
    endpoint = f"{url}/rest/v1/rpc/{function}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    # 10 minute timeout
    r = requests.post(endpoint, headers=headers, json=params, timeout=600)
    if r.status_code >= 400:
        print(f"Error {r.status_code}: {r.text}", file=sys.stderr)
        return None
    return r.json()

def main():
    parser = argparse.ArgumentParser(description="Supabase DB Operations")
    subparsers = parser.add_subparsers(dest="command")
    
    # RPC command
    rpc_parser = subparsers.add_parser("rpc")
    rpc_parser.add_argument("function", help="Function name")
    rpc_parser.add_argument("--params", help="JSON string of params", default="{}")
    
    args = parser.parse_args()
    url, key = get_config()
    
    if not url or not key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.", file=sys.stderr)
        sys.exit(1)
        
    if args.command == "rpc":
        params = json.loads(args.params)
        res = rpc(url, key, args.function, params)
        if res is not None:
            print(json.dumps(res, indent=2))
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
