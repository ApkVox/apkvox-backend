import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path("nba_engine")
DATASET_DB = BASE_DIR / "Data" / "dataset.sqlite"

try:
    with sqlite3.connect(DATASET_DB) as con:
        # Load a sample
        df = pd.read_sql_query('SELECT * FROM "dataset_2012-26" LIMIT 5', con)
        
        print("Columns with object type:")
        for col in df.columns:
            if df[col].dtype == 'object':
                print(f" - {col}: {df[col].unique()}")
                
                # Check for byte strings
                sample = df[col].iloc[0]
                print(f"   Sample value type: {type(sample)}")
                print(f"   Sample value: {sample}")

except Exception as e:
    print(f"Error: {e}")
