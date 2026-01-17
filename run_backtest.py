import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

# Add root to sys.path
sys.path.insert(0, os.getcwd())
from backend.predictor import get_prediction_service

class FinancialBacktester:
    def __init__(self, data_path="backtest_data.csv", initial_bankroll=1000):
        self.data_path = data_path
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.history = []
        self.service = get_prediction_service()
        
    def _american_to_decimal(self, odds):
        try:
            odds = float(odds)
            if odds > 0:
                return (odds / 100) + 1
            else:
                return (100 / abs(odds)) + 1
        except:
            return 1.0

    def run(self, strategy="kelly", threshold=0.10, start_date="2023-10-24", end_date="2024-06-20"):
        print(f"Starting Backtest (Strategy: {strategy}, Threshold: {threshold})...")
        
        # Load merged data
        try:
            df = pd.read_csv(self.data_path)
        except FileNotFoundError:
            print(f"Error: {self.data_path} not found.")
            return

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        
        # Filter for the requested period
        mask = (df["Date"] >= start_date) & (df["Date"] <= end_date)
        data = df[mask].copy()
        
        if len(data) == 0:
            print(f"No games found between {start_date} and {end_date}!")
            return

        print(f"Simulating on {len(data)} games from {start_date} to {end_date}...")
        
        # Load Model
        if not self.service.load_models():
            print("Failed to load models!")
            return
            
        # Prepare Features (X)
        import json
        try:
            with open("feature_columns.json", "r") as f:
                feature_cols = json.load(f)
            print(f"Loaded {len(feature_cols)} canonical features.")
        except FileNotFoundError:
            print("ERROR: feature_columns.json not found!")
            return

        # Check for missing columns
        missing = [c for c in feature_cols if c not in data.columns]
        if missing:
            print(f"Missing {len(missing)} features in backtest data (checking aliasing)...")
            renames = {}
            for m in missing:
                underscore_ver = m.replace("-", "_")
                if underscore_ver in data.columns:
                    renames[underscore_ver] = m
            if renames:
                data = data.rename(columns=renames)
            
            missing = [c for c in feature_cols if c not in data.columns]
            if missing:
                print(f"CRITICAL: Still missing {len(missing)} features: {missing[:5]}...")
                return

        # Strict selection order aligned with Unified Model
        X_df = data[feature_cols]
        X_df = X_df.reindex(sorted(X_df.columns), axis=1)
        X = X_df.values.astype(float)
            
        try:
            from nba_engine.src.Predict import XGBoost_Runner
            if XGBoost_Runner.xgb_ml is None:
                XGBoost_Runner._load_models()
            
            probs = XGBoost_Runner._predict_probs(XGBoost_Runner.xgb_ml, X, XGBoost_Runner.xgb_ml_calibrator)
            data["prob_home"] = probs[:, 1]
            data["prob_away"] = probs[:, 0]
            
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
            return

        # Simulation Loop
        bets_placed = 0
        stake_unit = self.initial_bankroll * 0.05 # 5% unit size
        
        # PARAMETERS
        MIN_ODDS = 1.60       # Stricter than 1.50
        MIN_EDGE = 0.15       # Stricter than 0.10 (Sniper Mode)
        KELLY_FRACTION = 0.25 # 1/4 Kelly
        
        print(f"Filters: Odds > {MIN_ODDS}, Edge > {MIN_EDGE}, Kelly {KELLY_FRACTION}")

        for loop_i, (idx, row) in enumerate(data.iterrows()):
            oh = row.get("odds_home", 0)
            oa = row.get("odds_away", 0)
            dec_h = self._american_to_decimal(oh)
            dec_a = self._american_to_decimal(oa)
            
            # Implied Probabilities
            h_implied = 1 / dec_h if dec_h > 0 else 1
            a_implied = 1 / dec_a if dec_a > 0 else 1
            
            # Edge Calculation
            h_edge = row["prob_home"] - h_implied
            a_edge = row["prob_away"] - a_implied
            
            bet_on = None
            bet_amt = 0
            bet_odds = 0
            
            # Debug first 5 rows
            if loop_i < 5:
                print(f"Game {loop_i}: H_Edge={h_edge:.2f} (Odds {dec_h}), A_Edge={a_edge:.2f} (Odds {dec_a})")

            # Selection Logic
            if strategy == "kelly":
                # Check Home
                if h_edge > MIN_EDGE and dec_h >= MIN_ODDS:
                    b = dec_h - 1
                    p = row["prob_home"]
                    f = p - (1 - p) / b
                    stake = self.bankroll * (f * KELLY_FRACTION)
                    if stake > 0:
                        bet_on = "Home"
                        bet_amt = stake
                        bet_odds = dec_h
                
                # Check Away
                elif a_edge > MIN_EDGE and dec_a >= MIN_ODDS:
                    b = dec_a - 1
                    p = row["prob_away"]
                    f = p - (1 - p) / b
                    stake = self.bankroll * (f * KELLY_FRACTION)
                    if stake > 0:
                        bet_on = "Away"
                        bet_amt = stake
                        bet_odds = dec_a
            
            # Execute Bet
            if bet_on:
                bets_placed += 1
                actual_home_win = (row["result_home_win"] == 1)
                result_win = (bet_on == "Home" and actual_home_win) or (bet_on == "Away" and not actual_home_win)
                
                if result_win:
                    profit = bet_amt * (bet_odds - 1)
                    self.bankroll += profit
                else:
                    self.bankroll -= bet_amt
                
                # Prevent negative bankroll
                if self.bankroll <= 0:
                    self.bankroll = 0
                    print(f"BANKRUPTCY at Game {loop_i}")
                    break
            
            self.history.append(self.bankroll)
            
        profit = self.bankroll - self.initial_bankroll
        roi = (profit / self.initial_bankroll) * 100
        
        print("\n=== Backtest Results ===")
        print(f"Period:           {start_date} to {end_date}")
        print(f"Initial Bankroll: ${self.initial_bankroll:,.2f}")
        print(f"Final Bankroll:   ${self.bankroll:,.2f}")
        print(f"Profit:           ${profit:,.2f}")
        print(f"ROI:              {roi:.2f}%")
        print(f"Total Bets:       {bets_placed}")
        print("========================")
        
        plt.figure()
        plt.plot(self.history)
        plt.title(f"Bankroll Growth ({strategy})")
        plt.xlabel("Games")
        plt.ylabel("Bankroll")
        plt.savefig("backtest_result.png")
        print("Chart saved to backtest_result.png")

if __name__ == "__main__":
    tester = FinancialBacktester(initial_bankroll=50000)
    # Most recent 4 months: roughly 2025-09-01 to 2026-01-07
    tester.run(strategy="kelly", start_date="2025-09-01", end_date="2026-01-07")
