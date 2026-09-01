import urllib.request
import json

def test_nba():
    url = "https://stats.nba.com/stats/commonallplayers?LeagueID=00&Season=2025-26&IsOnlyCurrentSeason=1"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nba.com/',
        'Origin': 'https://www.nba.com',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Connection': 'keep-alive',
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            rows = data['resultSets'][0]['rowSet']
            print(f"NBA: SUCCESS, got {len(rows)} players")
    except Exception as e:
        print(f"NBA: FAILED - {e}")

def test_mlb():
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            print(f"MLB: SUCCESS, got {len(data.get('teams', []))} teams")
    except Exception as e:
        print(f"MLB: FAILED - {e}")

test_nba()
test_mlb()
