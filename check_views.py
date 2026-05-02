import os
import requests

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
}

def query(table, params):
    endpoint = f"{url}/rest/v1/{table}"
    r = requests.get(endpoint, headers=headers, params=params)
    if r.status_code >= 400:
        print(f"Error {r.status_code}: {r.text}")
        return None
    return r.json()

# Check for a view that might have latest activity
print("Checking for views with 'active' or 'commander' in name...")
# We can't easily list tables via REST, but we can try common names or check migrations
