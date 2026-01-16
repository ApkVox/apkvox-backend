import sqlite3
import pandas as pd
from pathlib import Path

# Paths
DATA_DIR = Path("nba_engine/Data")
DATASET_DB = DATA_DIR / "dataset.sqlite"
ODDS_DB = DATA_DIR / "OddsData.sqlite"
OUTPUT_FILE = "backtest_data.csv"

# Columns to keep from dataset (Features + Target)
TARGET_COL = "Home-Team-Win"
# We need basic info to join: Date, TEAM_NAME (Home), TEAM_NAME.1 (Away)
JOIN_COLS = ["Date", "TEAM_NAME", "TEAM_NAME.1"]

def main():
    print("Loading Dataset...")
    with sqlite3.connect(DATASET_DB) as con:
        # Load 2024-25 data (most recent complete season?) or 2023-24
        # Let's try to load all and filter later
        # But tables are usually named "dataset_20xx-yy"
        # Let's get "dataset_2024-25" if exists, or iterate
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'dataset_%'")
        tables = [r[0] for r in cursor.fetchall()]
        print(f"Dataset tables: {tables}")
        
        dfs = []
        for t in tables:
            print(f"Reading {t}...")
            df = pd.read_sql_query(f'SELECT * FROM "{t}"', con)
            dfs.append(df)
            
        dataset = pd.concat(dfs, ignore_index=True)
    
    print(f"Total dataset rows: {len(dataset)}")
    
    # Ensure Date format
    # Force coerce to handle potential bad data, assume standard format if possible
    dataset["Date"] = pd.to_datetime(dataset["Date"], errors='coerce')
    dataset = dataset.dropna(subset=["Date"])
    
    print("Loading Odds...")
    with sqlite3.connect(ODDS_DB) as con:
        # Tables might be "odds_2023-24_new", "odds_2024-25", etc.
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'odds_%'")
        tables = [r[0] for r in cursor.fetchall()]
        print(f"Odds tables: {tables}")
        
        dfs = []
        for t in tables:
             # Skip old logic tables if needed, stick to consistent naming
             print(f"Reading {t}...")
             df = pd.read_sql_query(f'SELECT * FROM "{t}"', con)
             dfs.append(df)
        
        odds_df = pd.concat(dfs, ignore_index=True)
        
    print(f"Total odds rows: {len(odds_df)}")
    odds_df["Date"] = pd.to_datetime(odds_df["Date"], errors='coerce')
    odds_df = odds_df.dropna(subset=["Date"])
    
    # Clean Join Keys
    # Dataset: TEAM_NAME, TEAM_NAME.1
    # Odds: Home, Away
    
    # Merge
    print("Merging Data...")
    # Using 'Date' and Team names. Date might slightly mismatch (UTC vs Local)
    # We'll assume Dates match reasonably well or require slight fuzziness? 
    # For now strict merge on Date + Home Team
    
    # Renaming for consistent merge
    dataset = dataset.rename(columns={"TEAM_NAME": "Home", "TEAM_NAME.1": "Away"})
    
    # Note: Dataset Date might be different format?
    # Let's clean odds date too
    
    merged = pd.merge(dataset, odds_df, on=["Date", "Home", "Away"], how="inner", suffixes=("", "_odds"))
    
    print(f"Merged rows: {len(merged)}")
    
    if len(merged) == 0:
        print("WARNING: Zero rows merged. Check Date formats!")
        print("Dataset Date sample:", dataset["Date"].head())
        print("Odds Date sample:", odds_df["Date"].head())
        return

    # Select columns for backtest
    # We need: Date, Home, Away, Odds_Home, Odds_Away, Result (Home-Win), All Features
    
    # Rename Odds Columns to standard
    merged = merged.rename(columns={"ML_Home": "odds_home", "ML_Away": "odds_away", "Home-Team-Win": "result_home_win"})
    
    # Drop known metadata from features
    cols_to_drop = [
        "Score", "OU", "OU-Cover", "index", "index_odds", "Points", "Win_Margin", 
        "Days_Rest_Home_odds", "Days_Rest_Away_odds", "Spread", "OU_odds"
    ]
    merged = merged.drop(columns=[c for c in cols_to_drop if c in merged.columns], errors="ignore")
    
    print(f"Saving to {OUTPUT_FILE}...")
    merged.to_csv(OUTPUT_FILE, index=False)
    print("Done.")

if __name__ == "__main__":
    main()
