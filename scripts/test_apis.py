import urllib.request
import json
import os

api_key = os.environ.get("BALLDONTLIE_API_KEY")

def test(sport):
    url = f"https://api.balldontlie.io/{sport}/v1/players/active?per_page=5"
    req = urllib.request.Request(url, headers={"Authorization": api_key})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            print(f"=== {sport} ===")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"{sport}: FAILED - {e}")

test("wnba")
test("nhl")
