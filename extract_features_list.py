import sqlite3
import pandas as pd
import json
from pathlib import Path

DATA_DB = Path("nba_engine/Data/dataset.sqlite")
OUTPUT_JSON = "feature_columns.json"

def main():
    with sqlite3.connect(DATA_DB) as con:
        # Target the most comprehensive table
        table_name = "dataset_2012-26"
        print(f"Reading columns from {table_name}...")
        
        # Read 1 row to get columns
        df = pd.read_sql_query(f'SELECT * FROM "{table_name}" LIMIT 1', con)
        all_cols = df.columns.tolist()
        
    print(f"Total columns in dataset: {len(all_cols)}")
    
    # Define DROP columns (Training Targets + Metadata)
    # These must match EXACTLY what is dropped during training.
    # From investigation:
    drop_cols = [
        "Score", "Home-Team-Win", "OU", "OU-Cover", # Targets
        "Date", "Date.1",                           # Dates
        "TEAM_NAME", "TEAM_NAME.1"                  # Names
    ]
    
    # Also drop 'Unnamed: 0' if present
    
    feature_cols = [c for c in all_cols if c not in drop_cols and "Unnamed" not in c]
    
    print(f"Feature columns count: {len(feature_cols)}")
    
    if len(feature_cols) != 230:
        print(f"WARNING: Expected 230 features, found {len(feature_cols)}")
        # Print differences?
    
    with open(OUTPUT_JSON, "w") as f:
        json.dump(feature_cols, f, indent=2)
        
    print(f"Saved {len(feature_cols)} feature names to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
