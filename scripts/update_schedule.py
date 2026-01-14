from nba_api.stats.endpoints import leaguegamelog
import pandas as pd
from datetime import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent / "nba_engine" / "Data"
CSV_PATH = BASE_DIR / "nba-2025-UTC.csv"

# Map for Locations/Stadiums?
# LeagueGameLog doesn't provide stadium. 
# We might leave Location blank or generic. The App handles blank location.

def fetch_and_sync():
    print("Fetching Real Schedule for 2024-25 Season...")
    
    # Fetch Regular Season
    # season='2024-25' matches real life
    log = leaguegamelog.LeagueGameLog(season='2024-25', league_id='00', season_type_all_star='Regular Season')
    df_log = log.get_data_frames()[0]
    
    # Process
    # df_log has one row per Team per Game (2 rows per game).
    # We need to deduplicate to get 1 row per Game.
    # Columns: GAME_ID, GAME_DATE, TEAM_ID, TEAM_NAME, MATCHUP, WL, PTS...
    
    # Group by GAME_ID
    games = []
    grouped = df_log.groupby("GAME_ID")
    
    print(f"Found {len(grouped)} games.")
    
    match_number = 1
    
    for game_id, group in grouped:
        if len(group) != 2:
            continue
            
        # Identify Home/Away
        # MATCHUP column: "BOS @ DET" or "BOS vs. DET"
        # @ means Away @ Home.
        # vs. means Home vs. Away.
        
        row1 = group.iloc[0]
        row2 = group.iloc[1]
        
        matchup = row1["MATCHUP"]
        
        if "@" in matchup:
            # row1 is Away (at row2)
            away_team = row1["TEAM_NAME"]
            home_team = row2["TEAM_NAME"]
            away_score = row1["PTS"]
            home_score = row2["PTS"]
            date_str = row1["GAME_DATE"] # YYYY-MM-DD
        else:
            # row1 is Home (vs row2)
            home_team = row1["TEAM_NAME"]
            away_team = row2["TEAM_NAME"]
            home_score = row1["PTS"]
            away_score = row2["PTS"]
            date_str = row1["GAME_DATE"]

        # Parse Date
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        # YEAR SHIFT: 2024 -> 2025, 2025 -> 2026
        # Matches user simulation
        new_year = dt.year + 1
        new_dt = dt.replace(year=new_year)
        
        # Format for CSV: dd/mm/yyyy HH:MM
        # We don't have time produced by GameLog, defaulting to 23:00 UTC (7PM EST approx)
        csv_date = new_dt.strftime("%d/%m/%Y 23:00")
        
        # Result "Home - Away" (e.g. 110 - 105)
        # Only if Played (PTS > 0 generally, but checking for None)
        # If Future Game, PTS might be NaN or 0? 
        # GameLog usually only returns Played games?
        # WAIT. LeagueGameLog only returns COMPLETED games?
        # I need SCHEDULE for future games too!
        # LeagueGameLog returns past games.
        # For Schedule, I need `LeagueSchedule` endpoint? No such endpoint in easy access.
        # `ScoreboardV2` is day by day.
        
        # ALTERNATIVE: Use `CommonTeamYears`? No.
        # `videostatus`?
        
        # `nba_api` doesn't have a single "Get Full Schedule" endpoint easily?
        # Actually `data.nba.com` schedule URL? `http://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2024/league/00_full_schedule.json`
        
        result_str = ""
        if pd.notna(home_score) and pd.notna(away_score):
             result_str = f"{int(home_score)} - {int(away_score)}"
             
        games.append({
            "Match Number": match_number,
            "Round Number": 1, # Dummy
            "Date": csv_date,
            "Location": "NBA Arena", # Generic
            "Home Team": home_team,
            "Away Team": away_team,
            "Result": result_str
        })
        match_number += 1
        
    # Check if we need FUTURE games?
    # LeagueGameLog does NOT contain future games.
    # We rely on specific endpoint for schedule?
    # Or just use what we have (Past/Current games)?
    # User said "Obtener resultados reales".
    # If I only provide Past games, `predictor.py` can't predict Future.
    
    # I MUST get the Full Schedule. 
    # Use `static.nba.com` JSON?
    # Or simpler: Is there an endpoint in nba_api? `CommonAllPlayers`? No.
    
    pass

# We need a different approach for Full Schedule including Future.
# But for now, if I can just sync the *Existing* games to be correct...
# Wait, if I delete the CSV content, I lose the Future schedule.
# I MUST find a way to get the 2024-25 Schedule.

# Using `requests` to get full schedule JSON is better.
# URL: https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_2.json
# Standard NBA Schedule endpoint.

import requests




def fetch_full_schedule():
    print("Fetching Full NBA Schedule (2025-26 Source - CDN Static)...")
    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com"
    }
    r = requests.get(url, headers=headers)
    data = r.json()
    
    games_list = []
    
    # Structure: leagueSchedule -> gameDates -> games
    game_dates = data['leagueSchedule']['gameDates']
    match_number = 1
    
    for day in game_dates:
        # day['gameDate']
        
        for game in day['games']:
            # Extract Teams
            home = game['homeTeam']
            away = game['awayTeam']
            
            home_name = f"{home['teamCity']} {home['teamName']}"
            away_name = f"{away['teamCity']} {away['teamName']}"
            
            # Date Handling
            # gameDateTimeUTC: "2025-10-02T16:00:00Z"
            date_est = datetime.fromisoformat(game['gameDateTimeUTC'].replace('Z', '+00:00'))
            
            # NO YEAR SHIFT (Dates are already 2025/2026)
            new_dt = date_est
            
            csv_date = new_dt.strftime("%d/%m/%Y %H:%M")
            
            # Scores?
            home_score = home.get('score', '')
            away_score = away.get('score', '')
            
            result_str = ""
            if home_score and away_score:
                result_str = f"{home_score} - {away_score}"
            
            # Location
            loc = f"{game['arenaName']}, {game['arenaCity']}"
            
            games_list.append({
                "Match Number": match_number,
                "Round Number": 1,
                "Date": csv_date,
                "Location": loc,
                "Home Team": home_name,
                "Away Team": away_name,
                "Result": result_str
            })
            match_number += 1
            
    df = pd.DataFrame(games_list)
    print(f"Generated schedule with {len(df)} games.")
    
    # Save
    df.to_csv(CSV_PATH, index=False)
    print("Saved to CSV.")



if __name__ == "__main__":
    fetch_full_schedule()
