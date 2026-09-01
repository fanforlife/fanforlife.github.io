import pandas as pd
import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")
PT = ZoneInfo("America/Los_Angeles")

# nflverse and ESPN use slightly different abbreviations for a couple of teams
ESPN_ABBR_OVERRIDES = {
    "LA": "LAR",
    "WAS": "WSH",
}

def espn_abbr(team):
    return ESPN_ABBR_OVERRIDES.get(team, team)

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
    """date_str is YYYY-MM-DD. Returns {team_abbr: network_name} for games on that date."""
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

# ---- Roster + college data ----
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

# ---- Schedule + next game data ----
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
        info_base = {
            "date": kickoff.strftime("%a, %b %d, %Y"),
            "time_et": kickoff.strftime("%I:%M %p ET").lstrip("0"),
            "time_cst": kickoff.astimezone(CT).strftime("%I:%M %p Central").lstrip("0"),
            "time_pst": kickoff.astimezone(PT).strftime("%I:%M %p Pacific").lstrip("0"),
            "network": None,
        }
        if home not in next_game_by_team:
            next_game_by_team[home] = {**info_base, "opponent": f"vs {away}"}
            raw_gameday_by_team[home] = game['gameday']
        if away not in next_game_by_team:
            next_game_by_team[away] = {**info_base, "opponent": f"@ {home}"}
            raw_gameday_by_team[away] = game['gameday']

    # Fill in broadcast network via ESPN's public (unofficial) scoreboard endpoint
    unique_dates = set(raw_gameday_by_team.values())
    espn_network_by_date_team = {}
    for d in unique_dates:
        for abbr, net in fetch_espn_network(d).items():
            espn_network_by_date_team[(d, abbr)] = net

    for team, gameday in raw_gameday_by_team.items():
        network = espn_network_by_date_team.get((gameday, espn_abbr(team)))
        next_game_by_team[team]['network'] = network
        if network:
            print(f"{team}: {network}")
        else:
            print(f"{team}: no network found for {gameday}")

# ---- Merge next game info into roster ----
def attach_next_game(row):
    ng = next_game_by_team.get(row['team'])
    if ng:
        return pd.Series(ng)
    return pd.Series({
        "date": None, "time_et": None, "time_cst": None,
        "time_pst": None, "network": None, "opponent": None
    })

next_game_cols = roster_df.apply(attach_next_game, axis=1)
roster_df = pd.concat([roster_df.reset_index(drop=True), next_game_cols.reset_index(drop=True)], axis=1)
roster_df = roster_df.astype(object).where(pd.notnull(roster_df), None)

players = roster_df.to_dict(orient='records')

with open('players.json', 'w') as f:
    json.dump(players, f, indent=2)

print(f"Saved {len(players)} player-college rows")
