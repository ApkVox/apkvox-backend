from backend.database import get_history, init_db

init_db()

# Test get_history directly
records = get_history(limit=10, game_date="2026-01-13")
print(f"get_history returned: {len(records)} records")

if records:
    rec = records[0]
    print(f"Sample keys: {rec.keys()}")
    print(f"Sample: {rec}")
else:
    print("No records returned!")
    
    # Try without date filter
    all_recs = get_history(limit=5)
    print(f"All records: {len(all_recs)}")
    if all_recs:
        print(f"Sample game_date: {all_recs[0].get('game_date')}")
