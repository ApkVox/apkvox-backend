"""
AI Worker - Background Analysis Service

Runs independently from the API server to analyze teams
and cache results in SQLite for instant access.

Usage:
    python -m backend.ai_worker           # Analyze all teams for today
    python -m backend.ai_worker --team "Lakers"  # Analyze specific team
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.database import init_db, save_ai_insight, get_ai_insight
from backend.timezone import get_current_datetime, get_current_date

# Try to import AI Investigator
try:
    from ai_researcher import SportsInvestigator
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("[AI Worker] WARNING: ai_researcher module not available")


def get_todays_teams() -> list:
    """Get all unique teams playing today from schedule CSV."""
    import pandas as pd
    
    schedule_path = BASE_DIR / "nba_engine" / "Data" / "nba-2025-UTC.csv"
    
    try:
        df = pd.read_csv(schedule_path, parse_dates=["Date"], date_format="%d/%m/%Y %H:%M")
        
        today = get_current_datetime()
        target_date = today.date()
        
        # Adjust for NBA timezone (games after midnight UTC are still "today")
        nba_time = df["Date"] - timedelta(hours=6)
        todays_games = df[nba_time.dt.date == target_date]
        
        # Get unique teams
        home_teams = todays_games["Home Team"].tolist()
        away_teams = todays_games["Away Team"].tolist()
        
        all_teams = list(set(home_teams + away_teams))
        print(f"[AI Worker] Found {len(all_teams)} unique teams playing today")
        return all_teams
        
    except Exception as e:
        print(f"[AI Worker] Error reading schedule: {e}")
        return []


def analyze_team(investigator: 'SportsInvestigator', team_name: str, game_date: str) -> dict:
    """Run AI analysis for a single team."""
    print(f"\n[AI Worker] Analyzing {team_name}...")
    
    # Check if we already have a valid cache
    cached = get_ai_insight(team_name, game_date)
    if cached:
        print(f"[AI Worker] Using cached insight for {team_name}")
        return cached
    
    try:
        # Search for news
        news = investigator.search_news(f"{team_name} NBA injuries news")
        
        # Analyze impact
        analysis = investigator.analyze_impact(news, team_name)
        
        # Save to cache
        save_ai_insight(team_name, game_date, analysis)
        
        return analysis
        
    except Exception as e:
        print(f"[AI Worker] Error analyzing {team_name}: {e}")
        return {
            "summary": f"Error: {str(e)}",
            "impact_score": 0.0,
            "key_factors": [],
            "confidence": 0
        }


def run_daily_analysis():
    """Analyze all teams playing today."""
    if not AI_AVAILABLE:
        print("[AI Worker] Cannot run: AI Investigator not available")
        return
    
    print(f"\n{'='*60}")
    print(f"[AI Worker] Starting Daily Analysis - {get_current_datetime()}")
    print(f"{'='*60}")
    
    # Initialize
    init_db()
    investigator = SportsInvestigator()
    game_date = str(get_current_date())
    
    # Get teams
    teams = get_todays_teams()
    
    if not teams:
        print("[AI Worker] No teams to analyze today")
        return
    
    # Analyze each team
    success_count = 0
    for team in teams:
        try:
            result = analyze_team(investigator, team, game_date)
            if result.get("confidence", 0) > 0:
                success_count += 1
        except Exception as e:
            print(f"[AI Worker] Failed {team}: {e}")
    
    print(f"\n{'='*60}")
    print(f"[AI Worker] Completed: {success_count}/{len(teams)} teams analyzed")
    print(f"{'='*60}")


def run_single_analysis(team_name: str):
    """Analyze a single team (for on-demand requests)."""
    if not AI_AVAILABLE:
        print("[AI Worker] Cannot run: AI Investigator not available")
        return None
    
    init_db()
    investigator = SportsInvestigator()
    game_date = str(get_current_date())
    
    return analyze_team(investigator, team_name, game_date)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Analysis Worker")
    parser.add_argument("--team", type=str, help="Analyze specific team")
    args = parser.parse_args()
    
    if args.team:
        result = run_single_analysis(args.team)
        if result:
            import json
            print(f"\nResult:\n{json.dumps(result, indent=2)}")
    else:
        run_daily_analysis()
