"""
Audit Service
Compares stored predictions with actual NBA results.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

from .database import get_history, update_prediction_result
from .scores import fetch_scores_for_date

# Map full team names to abbreviations (Add more as needed or use a robust library)
# NotiaBet seems to use full names like "Lakers", "Heat" or "Los Angeles Lakers" in DB?
# We need to standardize. Assuming DB stores "Home Team" and "Away Team" names.
# The ScoresService returns Abbreviations (LAL, MIA).
# We need a mapping.

TEAM_MAP = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC",
    "L.A. Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "L.A. Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
    # Short names sometimes used
    "Hawks": "ATL", "Celtics": "BOS", "Nets": "BKN", "Hornets": "CHA",
    "Bulls": "CHI", "Cavaliers": "CLE", "Mavericks": "DAL", "Nuggets": "DEN",
    "Pistons": "DET", "Warriors": "GSW", "Rockets": "HOU", "Pacers": "IND",
    "Clippers": "LAC", "Lakers": "LAL", "Grizzlies": "MEM", "Heat": "MIA",
    "Bucks": "MIL", "Timberwolves": "MIN", "Pelicans": "NOP", "Knicks": "NYK",
    "Thunder": "OKC", "Magic": "ORL", "76ers": "PHI", "Suns": "PHX",
    "Trail Blazers": "POR", "Kings": "SAC", "Spurs": "SAS", "Raptors": "TOR",
    "Jazz": "UTA", "Wizards": "WAS"
}

def get_team_abbr(name: str) -> str:
    """Normalize team name to abbreviation"""
    return TEAM_MAP.get(name, name.upper()[:3]) # Fallback

def audit_predictions(date_obj: datetime) -> Dict[str, int]:
    """
    Audit predictions for a given date.
    
    1. Fetch predictions from DB for that date.
    2. Fetch actual scores from NBA API.
    3. Compare and update DB.
    
    Returns:
        Stats dict: { "audited": 5, "correct": 3 }
    """
    date_str = date_obj.strftime("%Y-%m-%d")
    print(f"[AuditService] Running audit for {date_str}")
    
    # 1. Get predictions
    # Note: get_history returns all, filtering efficiently or query by date
    # database.py has get_history(limit, game_date) -> Use that!
    predictions = get_history(limit=100, game_date=date_str)
    
    if not predictions:
        print(f"[AuditService] No predictions found for {date_str}")
        return {"audited": 0, "correct": 0}
        
    # 2. Fetch scores
    real_scores = fetch_scores_for_date(date_obj)
    
    if not real_scores:
        print(f"[AuditService] No scores available for {date_str}")
        return {"audited": 0, "correct": 0}
    
    # 3. Match and Update
    audited_count = 0
    correct_count = 0
    
    for pred in predictions:
        # DB status might already be FINAL, but we check anyway to update verification
        
        home_name = pred['home_team']
        away_name = pred['away_team']
        
        home_abbr = get_team_abbr(home_name)
        away_abbr = get_team_abbr(away_name)
        
        # Try to find match in real_scores
        # real_scores keys are "HOME:AWAY" (Abbr)
        key = f"{home_abbr}:{away_abbr}"
        
        match = real_scores.get(key)
        
        if not match:
            # Try inverted just in case? Or fuzzy match?
            # For now strict.
            continue
            
        if match["status"] == "FINAL":
            # Update DB
            success = update_prediction_result(
                game_date=date_str,
                home_team=home_name,
                away_team=away_name,
                home_score=match["home_score"],
                away_score=match["away_score"],
                status="FINAL"
            )
            
            if success:
                audited_count += 1
                # Check veridict logic is inside update_prediction_result?
                # Looking at database.py: YES, it calculates is_correct.
                
                # Check if it was correct (re-calculating locally for stats return)
                predicted_winner = pred["predicted_winner"]
                actual_winner_abbr = match["actual_winner"]
                
                # We need to know if predicted winner maps to actual winner abbr
                pred_abbr = get_team_abbr(predicted_winner)
                if pred_abbr == actual_winner_abbr:
                    correct_count += 1
                    
    print(f"[AuditService] Audit complete. Audited: {audited_count}, Matches found in scores source.")
    return {"audited": audited_count, "correct": correct_count}
