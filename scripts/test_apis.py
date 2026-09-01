import urllib.request
import json
import os

api_key = os.environ.get("BALLDONTLIE_API_KEY")

url = "https://api.balldontlie.io/nba/v1/players?per_page=5"
req = urllib.request.Request(url, headers={"Authorization": api_key})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"FAILED - {e}")
