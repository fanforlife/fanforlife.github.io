import pandas as pd
import json
import time
import urllib.request
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")
PT = ZoneInfo("America/Los_Angeles")

BDL_API_KEY = os.environ.get("BALLDONTLIE_API_KEY")

ESPN_ABBR_OVERRIDES = {"LA": "LAR", "WAS": "WSH"}
def espn_abbr(team):
    return ESPN_ABBR_OVERRIDES.get(team, team)

# ============ NFL (nflverse) ============
def try_year_roster(year):
    url = f"https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{year}.csv"
    try:
        df = pd.read_csv(url)
        if len(df) > 0:
            return df
    except Exception:
        return None
    return None

def load_schedules():
    current_year = datetime.now().year
    candidate_urls = [
        "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv",
        f"https://github.com/nflverse/nflverse-data/releases/download/schedules/sched_{current_year}.csv",
    ]
    for url in candidate_urls:
        try:
            df = pd.read_csv(url)
            if len(df) > 0:
                print(f"Loaded schedule data from {url}")
                return df
        except Exception as e:
            print(f"Could not load {url}: {e}")
    return None

def fetch_espn_network(date_str):
    yyyymmdd = date_str.replace("-", "")
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={yyyymmdd}"
    result = {}
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        for event in data.get('events', []):
            competitions = event.get('competitions', [])
            if not competitions:
                continue
            comp = competitions[0]
            network_names = []
            for b in comp.get('broadcasts', []):
                network_names.extend(b.get('names', []))
            network = network_names[0] if network_names else None
            if not network:
                continue
            for competitor in comp.get('competitors', []):
                abbr = competitor.get('team', {}).get('abbreviation')
                if abbr:
                    result[abbr] = network
    except Exception as e:
        print(f"ESPN fetch failed for {date_str}: {e}")
    return result

def load_injuries():
    current_year = datetime.now().year
    for year in [current_year, current_year - 1]:
        url = f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{year}.csv"
        try:
            df = pd.read_csv(url)
            if len(df) > 0:
                print(f"Loaded injury data from {url}")
                return df
        except Exception as e:
            print(f"Could not load {url}: {e}")
    return None

def build_injury_status_by_player():
    df = load_injuries()
    status_by_player = {}
    if df is not None and 'week' in df.columns:
        latest_week = df['week'].max()
        latest = df[df['week'] == latest_week]
        print(f"Using injury report data from week {latest_week}, {len(latest)} entries")
        for _, row in latest.iterrows():
            name = row.get('full_name')
            status = row.get('report_status')
            if pd.notna(name) and pd.notna(status):
                status_by_player[name] = status
    return status_by_player

def build_nfl_rows():
    current_year = datetime.now().year
    roster_df = try_year_roster(current_year)
    if roster_df is None or len(roster_df) == 0:
        roster_df = try_year_roster(current_year - 1)

    roster_df = roster_df[['full_name', 'team', 'position', 'college']].dropna(subset=['full_name'])
    roster_df['college'] = roster_df['college'].fillna('').astype(str).str.split(';')
    roster_df = roster_df.explode('college')
    roster_df['college'] = roster_df['college'].str.strip()
    roster_df = roster_df[roster_df['college'] != '']
    roster_df = roster_df.drop_duplicates(subset=['full_name', 'team', 'college'])

    sched_df = load_schedules()
    next_game_by_team = {}
    raw_gameday_by_team = {}

    if sched_df is not None and 'season' in sched_df.columns:
        sched_df = sched_df[sched_df['season'] == sched_df['season'].max()]

        def make_dt(row):
            try:
                date_str = row['gameday']
                time_str = row['gametime'] if pd.notna(row['gametime']) else "13:00"
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                return dt.replace(tzinfo=ET)
            except Exception:
                return None

        sched_df['kickoff_et'] = sched_df.apply(make_dt, axis=1)
        now_et = datetime.now(ET)
        upcoming = sched_df[sched_df['kickoff_et'].apply(lambda x: x is not None and x > now_et)].sort_values('kickoff_et')

        for _, game in upcoming.iterrows():
            kickoff = game['kickoff_et']
            home = game['home_team']
            away = game['away_team']
            central_str = kickoff.astimezone(CT).strftime("%I:%M%p").lstrip("0").lower()
            pacific_str = kickoff.astimezone(PT).strftime("%I:%M%p").lstrip("0").lower()
            date_part = kickoff.strftime("%a, %b") + " " + str(kickoff.day)
            info_base = {
                "next_game": f"{date_part} @ {central_str} Central / {pacific_str} Pacific",
                "kickoff_iso": kickoff.isoformat(),
                "network": None,
            }
            if home not in next_game_by_team:
                next_game_by_team[home] = {**info_base, "opponent": f"vs {away}"}
                raw_gameday_by_team[home] = game['gameday']
            if away not in next_game_by_team:
                next_game_by_team[away] = {**info_base, "opponent": f"@ {home}"}
                raw_gameday_by_team[away] = game['gameday']

        unique_dates = set(raw_gameday_by_team.values())
        espn_network_by_date_team = {}
        for d in unique_dates:
            for abbr, net in fetch_espn_network(d).items():
                espn_network_by_date_team[(d, abbr)] = net

        for team, gameday in raw_gameday_by_team.items():
            network = espn_network_by_date_team.get((gameday, espn_abbr(team)))
            next_game_by_team[team]['network'] = network

    def attach_next_game(row):
        ng = next_game_by_team.get(row['team'])
        if ng:
            return pd.Series(ng)
        return pd.Series({
            "next_game": None, "kickoff_iso": None, "network": None, "opponent": None
        })

    next_game_cols = roster_df.apply(attach_next_game, axis=1)
    roster_df = pd.concat([roster_df.reset_index(drop=True), next_game_cols.reset_index(drop=True)], axis=1)

    injury_status_by_player = build_injury_status_by_player()
    roster_df['injury_status'] = roster_df['full_name'].map(injury_status_by_player).fillna('')

    roster_df['sport'] = 'NFL'
    roster_df = roster_df.astype(object).where(pd.notnull(roster_df), None)
    return roster_df.to_dict(orient='records')

# ============ balldontlie (NBA + MLB) ============
def fetch_balldontlie_players(sport_path, active_only=False):
    all_players = []
    cursor = None
    page_count = 0
    endpoint = "players/active" if active_only else "players"
    while True:
        url = f"https://api.balldontlie.io/{sport_path}/v1/{endpoint}?per_page=100"
        if cursor is not None:
            url += f"&cursor={cursor}"
        req = urllib.request.Request(url, headers={"Authorization": BDL_API_KEY})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"{sport_path}: fetch failed on page {page_count}: {e}")
            break
        all_players.extend(data.get('data', []))
        cursor = data.get('meta', {}).get('next_cursor')
        page_count += 1
        print(f"{sport_path}: fetched page {page_count}, total so far {len(all_players)}")
        if not cursor:
            break
        time.sleep(13)
    return all_players

def build_nba_rows():
    raw = fetch_balldontlie_players("nba", active_only=True)
    rows = []
    for p in raw:
        college = p.get('college')
        if not college:
            continue
        full_name = f"{p.get('first_name','')} {p.get('last_name','')}".strip()
        team = (p.get('team') or {}).get('abbreviation')
        rows.append({
            "full_name": full_name, "team": team, "position": p.get('position'),
            "college": college, "sport": "NBA",
            "next_game": None, "kickoff_iso": None, "network": None, "opponent": None,
            "injury_status": None
        })
    return rows

def build_mlb_rows():
    raw = fetch_balldontlie_players("mlb")
    rows = []
    for p in raw:
        if not p.get('active'):
            continue
        college = p.get('college')
        if not college:
            continue
        team = (p.get('team') or {}).get('abbreviation')
        rows.append({
            "full_name": p.get('full_name'), "team": team, "position": p.get('position'),
            "college": college, "sport": "MLB",
            "next_game": None, "kickoff_iso": None, "network": None, "opponent": None,
            "injury_status": None
        })
    return rows

# ============ Combine and save ============
all_rows = []
all_rows.extend(build_nfl_rows())
# NBA and MLB temporarily disabled — NBA access is broken on balldontlie's end,
# pending their support response. Re-enable both lines below once resolved:
# all_rows.extend(build_nba_rows())
# all_rows.extend(build_mlb_rows())

with open('players.json', 'w') as f:
    json.dump(all_rows, f, indent=2)

with open('last_updated.json', 'w') as f:
    json.dump({"updated_at": datetime.now(timezone.utc).isoformat()}, f)

print(f"Saved {len(all_rows)} total player-college rows across all sports")
