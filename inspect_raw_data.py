import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("nba_engine/Data/TeamData.sqlite")

def main():
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found.")
        return

    try:
        with sqlite3.connect(DB_PATH) as con:
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            print(f"Tables found: {len(tables)}")
            print(f"Sample tables: {tables[:5]}")
            
            if tables:
                t = tables[-1] # Check most recent year usually at end
                print(f"Inspecting table: {t}")
                df = pd.read_sql_query(f'SELECT * FROM "{t}" LIMIT 1', con)
                print("Columns:")
                for c in df.columns:
                    print(f" - {c}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
