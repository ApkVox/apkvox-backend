"""
Autonomous Worker Module
========================

This module contains the "Brain" of the autonomous server.
It is responsible for:
1. Waking up at scheduled times (8am, 6pm).
2. Generating fresh predictions for the day.
3. Calculating the optimal betting strategy (Sniper Engine).
4. Running AI Risk Analysis (Sentinel).
5. Saving everything to the 'daily_cache' table for instant API retrieval.
"""

import traceback
from datetime import datetime
from threading import Thread

from backend.timezone import get_current_date
from backend.predictor import get_prediction_service
from backend import finance_engine
from backend.sentinel_agent import sentinel
from backend.database import save_daily_cache, save_predictions

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

        # 2. Generate Predictions (Heavy Lifting)
        # We explicitly request fresh predictions
        service = get_prediction_service()
        
        # Ensure models are loaded
        if not service.models_loaded:
            print("⚙️ [Autonomous Worker] Loading ML Models...")
            service.load_models()

        print("🔮 [Autonomous Worker] Generating predictions...")
        raw_predictions = service.get_upcoming_predictions(days=1, target_date=target_date)
        
        if raw_predictions:
            # Persist raw predictions to history
            save_predictions(raw_predictions)
            print(f"✅ [Autonomous Worker] Saved {len(raw_predictions)} raw predictions to DB")
        else:
            print("⚠️ [Autonomous Worker] No games found for today.")
            # We still save an empty cache to indicate we checked
            save_daily_cache(
                entry_date=target_date_str, 
                predictions=[], 
                strategy={"error": "No games found"}, 
                sentinel_msg="No games scheduled for today."
            )
            return

        # 3. Calculate Strategy (Sniper Engine)
        # We use a default bankroll of 1000 to calculate proportions/units, 
        # but the frontend will recalculate with user's actual bankroll.
        # This cache serves as the "Global Recommendation"
        print("🎯 [Autonomous Worker] Running Sniper Engine...")
        default_bankroll = 10000 
        proposed_bets = finance_engine.optimize_portfolio(raw_predictions, default_bankroll)
        
        bets_dicts = [bet.model_dump() for bet in proposed_bets]
        
        # 4. Sentinel Risk Analysis
        print("🛡️ [Autonomous Worker] Consulting Sentinel AI...")
        try:
            risk_advice = sentinel.analyze_risk(bets_dicts, default_bankroll)
        except Exception as e:
            print(f"❌ [Autonomous Worker] Sentinel failed: {e}")
            risk_advice = "Sentinel is offline temporarily."

        # 5. Save to Daily Cache
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
