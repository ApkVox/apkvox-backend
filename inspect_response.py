import requests
import json

try:
    response = requests.get("http://localhost:8000/api/predictions?date=2026-01-13")
    data = response.json()
    
    print(f"Count: {data.get('count', 0)}")
    for p in data.get('predictions', []):
        print(f"Game: {p.get('home_team')} vs {p.get('away_team')}")
        print(f"  Status: '{p.get('status')}'")
        print(f"  Scores: {p.get('home_score')} - {p.get('away_score')}")
        print(f"  Winner: {p.get('actual_winner')}")
        print("-" * 20)
        
except Exception as e:
    print(f"Error: {e}")
