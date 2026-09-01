import pandas as pd
import json
from datetime import datetime

def try_year(year):
    url = f"https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{year}.csv"
    try:
        df = pd.read_csv(url)
        if len(df) > 0:
            return df
    except Exception:
        return None
    return None

current_year = datetime.now().year
df = try_year(current_year)
if df is None or len(df) == 0:
    df = try_year(current_year - 1)

df = df[['full_name', 'team', 'position', 'college']].dropna(subset=['full_name'])
df = df.drop_duplicates(subset=['full_name', 'team'])
df = df.astype(object).where(pd.notnull(df), None)

players = df.to_dict(orient='records')

with open('players.json', 'w') as f:
    json.dump(players, f, indent=2)

print(f"Saved {len(players)} players")
