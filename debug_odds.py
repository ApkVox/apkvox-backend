import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("nba_engine/Data/OddsData.sqlite")

try:
    with sqlite3.connect(DB_PATH) as con:
        # List tables
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables: {tables}")
        
        if tables:
            first_table = tables[0][0]
            df = pd.read_sql_query(f'SELECT * FROM "{first_table}" LIMIT 1', con)
            print(f"\nColumns in '{first_table}':")
            for c in df.columns.tolist():
                print(f" - {c}")
            
except Exception as e:
    print(f"Error: {e}")
