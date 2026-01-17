"""
Autonomous Worker Module
========================

This module contains the "Brain" of the autonomous server.
It is responsible for:
1. Waking up at scheduled times (8am, 6pm).
2. [NEW] Searching for news/injuries for ALL teams playing today (blocking step).
3. Generating fresh predictions for the day (using the AI insights).
4. Calculating the optimal betting strategy (Sniper Engine).
5. Running AI Risk Analysis (Sentinel).
6. Saving everything to the 'daily_cache' table for instant API retrieval.
"""

import traceback
import time
from datetime import datetime
from threading import Thread
from typing import List

from backend.timezone import get_current_date
from backend.predictor import get_prediction_service
from backend import finance_engine
from backend.sentinel_agent import sentinel
from backend.database import save_daily_cache, save_predictions, save_ai_insight

# Import AI Researcher
from ai_researcher import SportsInvestigator

def run_ai_investigation_batch(teams: List[str], game_date: str):
    """
    Runs the AI Researcher for a list of teams.
    This is a BLOCKING operation to ensure data is ready before prediction.
    """
    print(f"🕵️ [AI Worker] Starting investigation for {len(teams)} teams...")
    investigator = SportsInvestigator()
    
    for team in teams:
        try:
            # 1. Search News (Injuries, lineups)
            query = f"{team} NBA injuries news lineup"
            news_context = investigator.search_news(query)
            
            # 2. Analyze Impact
            analysis = investigator.analyze_impact(news_context, team)
            
            # 3. Save to DB
            save_ai_insight(team, game_date, analysis)
            print(f"✅ [AI Worker] Insight saved for {team} (Impact: {analysis.get('impact_score')})")
            
            # Rate limiting to avoid API bans (DuckDuckGo/Groq)
            time.sleep(2) 
            
        except Exception as e:
            print(f"❌ [AI Worker] Failed to investigate {team}: {e}")

    print("🏁 [AI Worker] Investigation batch complete.")


def run_daily_analysis(force_date=None):
    """
    The main autonomous routine.
    Can be triggered by Scheduler or manually via API.
    
    Args:
        force_date (str, optional): 'YYYY-MM-DD' to force analysis for a specific date.
                                    If None, uses today's date (NBA time).
    """
    print("🤖 [Autonomous Worker] Waking up to analyze the market...")
    
    try:
        # 1. Determine Date
        if force_date:
            target_date_str = force_date
            target_date = datetime.strptime(force_date, "%Y-%m-%d")
        else:
            target_date = datetime.combine(get_current_date(), datetime.min.time())
            target_date_str = target_date.strftime("%Y-%m-%d")

        print(f"📅 [Autonomous Worker] Target Date: {target_date_str}")
        
        service = get_prediction_service()
        
        # ---------------------------------------------------------
        # PHASE 1: IDENTIFY TEAMS & RUN AI RESEARCH (The "Brain" First)
        # ---------------------------------------------------------
        # We need to know who is playing to investigate them.
        # We'll use the service's internal helper or odds provider to get the game list WITHOUT predicting yet.
        # But `service.get_upcoming_predictions` does everything.
        # So we can look at the schedule first.
        
        matches = service._get_games_from_schedule(target_date)
        if not matches:
             # Try odds as fallback if schedule is empty (sometimes CSV is outdated)
             odds = service._get_odds()
             if odds:
                 from src.Utils.tools import create_todays_games_from_odds
                 raw_games = create_todays_games_from_odds(odds) # returns tuples
                 matches = [[g[0], g[1], ''] for g in raw_games]

        if not matches:
            print("⚠️ [Autonomous Worker] No games found for today to investigate.")
            # We exit early - no point predicting nothing.
            save_daily_cache(
                entry_date=target_date_str, 
                predictions=[], 
                strategy={"error": "No games found"}, 
                sentinel_msg="No games scheduled for today."
            )
            return

        # Extract unique teams
        teams_to_investigate = []
        for game in matches:
            teams_to_investigate.append(game[0]) # Home
            teams_to_investigate.append(game[1]) # Away
        
        # RUN THE BLOCKING RESEARCH
        # "Quiero que las predicciones no estén listas si el agente no tiene la investigación"
        run_ai_investigation_batch(teams_to_investigate, target_date_str)
        
        # ---------------------------------------------------------
        # PHASE 2: GENERATE PREDICTIONS (Now using the fresh AI data)
        # ---------------------------------------------------------
        
        # Ensure models are loaded
        if not service.models_loaded:
            print("⚙️ [Autonomous Worker] Loading ML Models...")
            service.load_models()

        print("🔮 [Autonomous Worker] Generating predictions (taking AI insights into account)...")
        # outcomes will automatically read from ai_insights table
        raw_predictions = service.get_upcoming_predictions(days=1, target_date=target_date)
        
        if raw_predictions:
            # Persist raw predictions to history
            save_predictions(raw_predictions)
            print(f"✅ [Autonomous Worker] Saved {len(raw_predictions)} raw predictions to DB")
        else:
            print("⚠️ [Autonomous Worker] Predictions returned empty (unexpected after schedule check).")
            return

        # ---------------------------------------------------------
        # PHASE 3: STRATEGY & SENTINEL
        # ---------------------------------------------------------
        print("🎯 [Autonomous Worker] Running Sniper Engine...")
        default_bankroll = 10000 
        proposed_bets = finance_engine.optimize_portfolio(raw_predictions, default_bankroll)
        
        bets_dicts = [bet.model_dump() for bet in proposed_bets]
        
        print("🛡️ [Autonomous Worker] Consulting Sentinel AI (Risk Analysis)...")
        try:
            risk_advice = sentinel.analyze_risk(bets_dicts, default_bankroll)
        except Exception as e:
            print(f"❌ [Autonomous Worker] Sentinel failed: {e}")
            risk_advice = "Sentinel is offline temporarily."

        # ---------------------------------------------------------
        # PHASE 4: SAVE TO CACHE
        # ---------------------------------------------------------
        strategy_payload = {
            "strategy": "Sniper (Edge > 15%, Odds > 1.60) [Cached]",
            "bankroll_basis": default_bankroll,
            "proposed_bets": bets_dicts,
            "risk_analysis": {
                "advisor": "Sentinel AI",
                "message": risk_advice,
                "exposure_rating": "HIGH" if len(bets_dicts) > 5 else "MODERATE"
            },
            "generated_at": datetime.now().isoformat()
        }

        success = save_daily_cache(
            entry_date=target_date_str,
            predictions=raw_predictions,
            strategy=strategy_payload,
            sentinel_msg=risk_advice
        )

        if success:
            print("💾 [Autonomous Worker] Analysis successfully cached!")
        else:
            print("❌ [Autonomous Worker] Failed to save to cache.")

    except Exception as e:
        print(f"💥 [Autonomous Worker] CRITICAL FAILURE: {e}")
        traceback.print_exc()

def start_analysis_thread():
    """Helper to run analysis in background without blocking"""
    t = Thread(target=run_daily_analysis)
    t.start()
