import pandas as pd
from datetime import datetime

current_year = datetime.now().year
url = f"https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{current_year}.csv"
df = pd.read_csv(url)

match = df[df['full_name'].str.contains('Rogers', case=False, na=False) & (df['team'] == 'LV')]
print("Matching rows in raw source data:")
print(match[['full_name', 'team', 'position', 'college', 'jersey_number', 'status']].to_string())

print("\nAll LV players with Texas Tech listed:")
tt = df[(df['team'] == 'LV') & (df['college'].str.contains('Texas Tech', case=False, na=False))]
print(tt[['full_name', 'team', 'college', 'jersey_number', 'status']].to_string())
