import pandas as pd
from datetime import datetime

current_year = datetime.now().year

for year in [current_year, current_year - 1]:
    url = f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{year}.csv"
    try:
        df = pd.read_csv(url)
        print(f"=== {year}: loaded {len(df)} rows ===")
        print("Columns:", list(df.columns))
        if len(df) > 0:
            print("Week range:", df['week'].min(), "to", df['week'].max())
            latest = df[df['week'] == df['week'].max()]
            print(f"Rows in latest week: {len(latest)}")
            print("Sample report_status values:", latest['report_status'].dropna().unique()[:10])
            print("Sample names:", latest['full_name'].head(5).tolist())
        break
    except Exception as e:
        print(f"{year}: FAILED - {e}")
