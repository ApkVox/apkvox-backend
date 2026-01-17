"""
The Sniper Engine (Financial Logic)

This module handles:
1. Kelly Criterion for Money Management
2. Sniper Filter (Edge & Odds checks)
3. Portfolio Optimization
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime
from .models import PredictionGame, BetLedger

# --- CONFIGURATION ---
KELLY_FRACTION = 0.25  # Conservative Kelly (1/4)
MIN_EDGE = 0.15        # 15% Edge required
MIN_ODDS = 1.60        # Minimum odds (decimal)
MAX_STAKE_PERCENT = 0.05 # Max 5% of bankroll per bet

def calculate_kelly_bet(win_prob: float, odds: float, bankroll: float, kelly_fraction: float = KELLY_FRACTION) -> float:
    """
    Calculates the optimal bet size using the Kelly Criterion.
    
    Formula: f* = (p * b - q) / b
    where:
        f* is the fraction of the current bankroll to wager
        b is the net odds received on the wager (odds - 1)
        p is the probability of winning
        q is the probability of losing (1 - p)
    """
    if odds <= 1:
        return 0.0
        
    b = odds - 1
    q = 1.0 - win_prob
    
    f_star = (win_prob * b - q) / b
    
    if f_star <= 0:
        return 0.0
        
    # Apply safety fraction (Kelly Fraction)
    safe_fraction = f_star * kelly_fraction
    
    # Calculate amount
    stake = bankroll * safe_fraction
    
    # Apply Cap (Risk Management)
    max_stake = bankroll * MAX_STAKE_PERCENT
    return min(stake, max_stake)

def sniper_check(win_prob: float, odds: float) -> Tuple[bool, float]:
    """
    Determines if a bet meets the 'Sniper' criteria.
    Returns (Passed, Edge)
    """
    if odds <= 1:
        return False, 0.0
        
    implied_prob = 1 / odds
    edge = win_prob - implied_prob
    
    pass_edge = edge > MIN_EDGE
    pass_odds = odds > MIN_ODDS
    
    return (pass_edge and pass_odds), edge

def optimize_portfolio(predictions: List[Dict[str, Any]], bankroll: float) -> List[BetLedger]:
    """
    Takes a list of raw prediction dicts (or models), applies filters,
    and returns a list of proposed Bets (BetLedger objects).
    """
    proposed_bets = []
    
    for pred in predictions:
        # Check Home Bet
        home_odds = pred.get('home_odds', 0)
        home_prob = pred.get('home_win_probability', 50) / 100.0
        
        is_sniper, edge = sniper_check(home_prob, home_odds)
        
        if is_sniper:
            stake = calculate_kelly_bet(home_prob, home_odds, bankroll)
            if stake > 0:
                bet = BetLedger(
                    prediction_id=pred.get('game_id', f"{pred.get('home_team')} vs {pred.get('away_team')}"),
                    date=pred.get('start_time_utc', datetime.now().isoformat())[:10],
                    match=f"{pred.get('home_team')} vs {pred.get('away_team')}",
                    selection=pred.get('home_team'), # Betting on Home
                    odds=home_odds,
                    stake_amount=round(stake, 2),
                    status="PENDING",
                    is_real_bet=False # Proposal
                )
                proposed_bets.append(bet)
                
        # Check Away Bet
        away_odds = pred.get('away_odds', 0)
        away_prob = pred.get('away_win_probability', 50) / 100.0
        
        is_sniper_a, edge_a = sniper_check(away_prob, away_odds)
        
        if is_sniper_a:
            stake = calculate_kelly_bet(away_prob, away_odds, bankroll)
            if stake > 0:
                bet = BetLedger(
                    prediction_id=pred.get('game_id', f"{pred.get('home_team')} vs {pred.get('away_team')}"),
                    date=pred.get('start_time_utc', datetime.now().isoformat())[:10],
                    match=f"{pred.get('home_team')} vs {pred.get('away_team')}",
                    selection=pred.get('away_team'), # Betting on Away
                    odds=away_odds,
                    stake_amount=round(stake, 2),
                    status="PENDING",
                    is_real_bet=False
                )
                proposed_bets.append(bet)
                
    return proposed_bets
