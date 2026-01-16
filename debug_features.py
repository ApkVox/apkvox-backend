import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path("nba_engine")
DATASET_DB = BASE_DIR / "Data" / "dataset.sqlite"

try:
    with sqlite3.connect(DATASET_DB) as con:
        # Load a sample
        df = pd.read_sql_query('SELECT * FROM "dataset_2012-26" LIMIT 1', con)
        
        print(f"Total columns in dataset: {len(df.columns)}")
        print("\nColumn names:")
        for i, col in enumerate(df.columns):
            print(f"  {i}: {col}")
            
        # Count non-metadata columns (those used for prediction)
        metadata_cols = ["Score", "Home-Team-Win", "OU", "OU-Cover", "Days-Rest-Home", "Days-Rest-Away", 
                        "TEAM_NAME", "TEAM_NAME.1", "Date", "Date.1"]
        feature_cols = [c for c in df.columns if c not in metadata_cols and "TEAM_" not in c and "Date" not in c]
        print(f"\nFeature columns (excluding metadata): {len(feature_cols)}")

except Exception as e:
    print(f"Error: {e}")
