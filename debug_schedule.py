import os
import sys
from datetime import datetime
import pandas as pd
from pathlib import Path

# Add root and nba_engine to sys.path
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "nba_engine"))

from backend.predictor import NBAPredictionService

service = NBAPredictionService()
schedule_df = service._load_schedule()
print(f"Schedule loaded: {len(schedule_df)} rows")

target_date_str = "2026-01-15"
target_date = datetime.strptime(target_date_str, "%Y-%m-%d")

nba_time = schedule_df["Date"] - pd.Timedelta(hours=6)
games_today = schedule_df[nba_time.dt.date == target_date.date()]

print(f"Found {len(games_today)} games for {target_date_str} in debug script.")
for _, row in games_today.iterrows():
    print(f"  {row['Away Team']} @ {row['Home Team']} ({row['Date']})")

# Try service method
games = service._get_games_from_schedule(target_date)
print(f"Service _get_games_from_schedule returned {len(games)} games.")
