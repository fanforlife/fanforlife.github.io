import urllib.request
import urllib.error
import os

api_key = os.environ.get("BALLDONTLIE_API_KEY")

url = "https://api.balldontlie.io/nba/v1/players/active?per_page=5"
req = urllib.request.Request(url, headers={"Authorization": api_key})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("SUCCESS")
        print("Headers:", dict(resp.headers))
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.reason}")
    print("Headers:", dict(e.headers))
    print("Body:", e.read().decode())
