import pandas as pd
import json
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")
PT = ZoneInfo("America/Los_Angeles")

NETWORK_LINKS = {
    "CBS": "https://www.cbssports.com/watch/",
    "FOX": "https://www.fox.com/live/",
    "NBC": "https://www.nbc.com/live",
    "ESPN": "https://www.espn.com/watch/",
    "ABC": "https://abc.com/watch-live",
    "NFLN": "https://www.nfl.com/network/",
    "Amazon": "https://www.amazon.com/gp/video/storefront",
    "Prime Video": "https://www.amazon.com/gp/video/storefront",
    "Peacock": "https://www.peacocktv.com/",
}

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

if sched_df is not None and 'season' in sched_df.columns:
    sched_df = sched_df[sched_df['season'] == sched_df['season'].max()]

        print("Schedule columns:", list(sched_df.columns))
    if 'network' in sched_df.columns:
        print("Sample network values:", sched_df['network'].dropna().unique()[:10])
    else:
        print("No 'network' column in this data")

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
        network = game.get('network', None)
        network = None if pd.isna(network) else str(network)
        info_base = {
            "date": kickoff.strftime("%a, %b %d, %Y"),
            "time_et": kickoff.strftime("%I:%M %p ET").lstrip("0"),
            "time_cst": kickoff.astimezone(CT).strftime("%I:%M %p Central").lstrip("0"),
            "time_pst": kickoff.astimezone(PT).strftime("%I:%M %p Pacific").lstrip("0"),
            "network": network,
        }
        home = game['home_team']
        away = game['away_team']
        if home not in next_game_by_team:
            next_game_by_team[home] = {**info_base, "opponent": f"vs {away}"}
        if away not in next_game_by_team:
            next_game_by_team[away] = {**info_base, "opponent": f"@ {home}"}

# ---- Merge next game info into roster ----
def attach_next_game(row):
    ng = next_game_by_team.get(row['team'])
    if ng:
        return pd.Series(ng)
    return pd.Series({
        "date": None, "time_et": None, "time_cst": None,
        "time_pst": None, "network": None, "network_link": None, "opponent": None
    })

next_game_cols = roster_df.apply(attach_next_game, axis=1)
roster_df = pd.concat([roster_df.reset_index(drop=True), next_game_cols.reset_index(drop=True)], axis=1)
roster_df = roster_df.astype(object).where(pd.notnull(roster_df), None)

players = roster_df.to_dict(orient='records')

with open('players.json', 'w') as f:
    json.dump(players, f, indent=2)

print(f"Saved {len(players)} player-college rows")
