import sqlite3

conn = sqlite3.connect('backend/app.db')
c = conn.cursor()

# Check what records exist
c.execute("SELECT game_date, home_team, away_team FROM predictions ORDER BY game_date DESC LIMIT 20")
rows = c.fetchall()

print(f"Found {len(rows)} recent records:")
for r in rows:
    print(f"  {r[0]}: {r[1]} vs {r[2]}")

# Check if any Jan 13 records exist
c.execute("SELECT COUNT(*) FROM predictions WHERE game_date = '2026-01-13'")
jan13_count = c.fetchone()[0]
print(f"\nJan 13 records: {jan13_count}")

# Check if any Jan 14 records exist  
c.execute("SELECT COUNT(*) FROM predictions WHERE game_date = '2026-01-14'")
jan14_count = c.fetchone()[0]
print(f"Jan 14 records: {jan14_count}")

conn.close()
