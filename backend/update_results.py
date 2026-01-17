"""
Daily Reconciliation Script (Cron Job)

1. Fetches Pending Bets.
2. Gets Game Outcomes.
3. Updates Bet Status (WON/LOST/VOID) & PnL.
4. Updates Portfolio History.
"""

import sys
import os
from datetime import datetime, timedelta

# Add root to sys.path to allow imports
sys.path.insert(0, os.getcwd())

from backend import database
from backend.scores import fetch_scores_from_csv # Or generic fetcher
# Assuming we can reuse generic scoring logic or fetch fresh from scores module

def reconcile_bets():
    print(f"--- Starting Reconciliation {datetime.now()} ---")
    
    # 1. Get Pending Bets
    pending_bets = database.get_pending_bets()
    if not pending_bets:
        print("No pending bets found.")
        return

    print(f"Found {len(pending_bets)} pending bets.")
    
    # 2. Get Scores (Logic: Fetch for unique dates in pending bets)
    unique_dates = set(bet['date'] for bet in pending_bets) # bet['date'] is datetime.date object 
    
    scores_cache = {} # date -> list of games
    
    for d in unique_dates:
        # Convert date to string YYYY-MM-DD if needed by score fetcher
        d_str = d.strftime("%Y-%m-%d") if isinstance(d, datetime) else str(d)
        scores = fetch_scores_from_csv(d_str) # Returns list of dicts with home, away, score
        scores_cache[d] = scores
        
    resolved_count = 0
    total_pnl = 0.0
    
    for bet in pending_bets:
        bet_date = bet['date']
        # bet matches structure: prediction_id, date, match, selection, odds, stake, status...
        
        games_on_date = scores_cache.get(bet_date, [])
        
        match_found = False
        for game in games_on_date:
            # Simple matching by string containment or exact team names
            # bet['match'] usually "Home vs Away"
            home = game.get('home_team', '')
            away = game.get('away_team', '')
            
            # Robust matching: check if both teams appear in the match string
            if home in bet['match'] and away in bet['match']:
                match_found = True
                
                # Check outcome
                if game['status'] == 'FINAL':
                    h_score = int(game['home_score'])
                    a_score = int(game['away_score'])
                    
                    won = False
                    
                    if bet['selection'] == home:
                        won = h_score > a_score
                    elif bet['selection'] == away:
                        won = a_score > h_score
                    # Implement Over/Under logic here if needed
                    
                    if won:
                        profit = (bet['stake_amount'] * bet['odds']) - bet['stake_amount']
                        database.update_bet_status(bet['id'], "WON", profit)
                        print(f"✅ Bet {bet['id']} WON: {bet['match']} ({bet['selection']}) +${profit:.2f}")
                        total_pnl += profit
                    else:
                        loss = -bet['stake_amount']
                        database.update_bet_status(bet['id'], "LOST", loss)
                        print(f"❌ Bet {bet['id']} LOST: {bet['match']} ({bet['selection']}) -${abs(loss):.2f}")
                        total_pnl += loss
                    
                    resolved_count += 1
                break
        
        if not match_found:
            # Maybe game hasn't happened yet or name mismatch
            pass

    print(f"Resolved {resolved_count} bets. Total Daily PnL: ${total_pnl:.2f}")
    
    # 4. Update Portfolio Snapshot (Simplified)
    # Ideally should read previous balance + pnl.
    # For now, let's just log the daily impact.
    if resolved_count > 0:
        # Fetch last portfolio snapshot
        history = database.get_portfolio_history(limit=1)
        current_balance = history[0]['total_balance'] if history else 50000.0 # Default starting bank
        
        new_balance = current_balance + total_pnl
        today = datetime.now().date()
        
        from backend.models import PortfolioSnapshot
        snap = PortfolioSnapshot(
            date=str(today),
            total_balance=new_balance,
            daily_profit=total_pnl,
            roi_percentage=((new_balance - 50000)/50000)*100
        )
        database.save_portfolio_snapshot(snap)
        print(f"Updated Portfolio: New Balance ${new_balance:.2f}")

if __name__ == "__main__":
    reconcile_bets()
