import pandas as pd
from datetime import datetime

current_year = datetime.now().year

# 1. Full column list from the roster file (answers "what fields exist")
url = f"https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{current_year}.csv"
df = pd.read_csv(url)
print("=== ALL ROSTER COLUMNS ===")
print(list(df.columns))

print("\n=== UNIQUE STATUS VALUES IN CURRENT DATA ===")
print(df['status'].value_counts())

# 2. Check if depth chart data (real starter/2nd/3rd string rank) is available this season
depth_url = f"https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_{current_year}.csv"
try:
    depth_df = pd.read_csv(depth_url)
    print(f"\n=== DEPTH CHART DATA: loaded {len(depth_df)} rows ===")
    print("Columns:", list(depth_df.columns))
    print("Weeks available:", sorted(depth_df['week'].unique()))
    print("Sample rows for one team:")
    print(depth_df[depth_df['club_code'] == 'LV'].head(10).to_string())
except Exception as e:
    print(f"\nDepth chart data not available yet for {current_year}: {e}")
