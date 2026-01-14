"""
NBA Prediction Service Wrapper

Isolates the nba_engine prediction logic from the CLI interface,
providing a clean API for FastAPI integration.
"""

import sys
import io
import contextlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Timezone-aware date handling
from .timezone import get_current_datetime, get_current_timestamp, NBA_TIMEZONE

import numpy as np
import pandas as pd
import xgboost as xgb

# ============================================================
# CRITICAL: Add nba_engine to sys.path BEFORE importing modules
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
NBA_ENGINE_PATH = BASE_DIR / "nba_engine"
sys.path.insert(0, str(NBA_ENGINE_PATH))

# Now we can import from nba_engine (XGBoost only, NO TensorFlow/NN)
# Import the module so we can access globals that are set after _load_models()
from src.Predict import XGBoost_Runner
from src.Predict.XGBoost_Runner import (
    _load_models as load_xgb_models,
    _predict_probs,
)
from src.Utils.tools import get_json_data, to_data_frame, create_todays_games_from_odds
from src.Utils.Dictionaries import team_index_current
from src.DataProviders.SbrOddsProvider import SbrOddsProvider

# Database persistence
from .database import save_predictions

# URLs from original main.py
TODAYS_GAMES_URL = "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2025/scores/00_todays_scores.json"
DATA_URL = "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&Height=&ISTRound=&LastNGames=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2025-26&SeasonSegment=&SeasonType=Regular%20Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="
SCHEDULE_PATH = NBA_ENGINE_PATH / "Data" / "nba-2025-UTC.csv"


class NBAPredictionService:
    """
    Service class for NBA game predictions using XGBoost models.
    Designed for API integration without console output pollution.
    """

    def __init__(self, sportsbook: str = "fanduel"):
        self.sportsbook = sportsbook
        self.models_loaded = False
        self._schedule_df: Optional[pd.DataFrame] = None

    def _silence_output(self, func, *args, **kwargs):
        """Execute function while suppressing stdout/stderr"""
        with contextlib.redirect_stdout(io.StringIO()):
            with contextlib.redirect_stderr(io.StringIO()):
                return func(*args, **kwargs)

    def load_models(self) -> bool:
        """Load XGBoost models into memory"""
        try:
            # Don't silence this - globals need to be set
            load_xgb_models()
            self.models_loaded = True
            print("[NBAPredictionService] XGBoost models loaded successfully")
            return True
        except Exception as e:
            print(f"[NBAPredictionService] Error loading models: {e}")
            return False

    def _load_schedule(self) -> pd.DataFrame:
        """Load the NBA schedule CSV"""
        if self._schedule_df is None:
            self._schedule_df = pd.read_csv(
                SCHEDULE_PATH,
                parse_dates=["Date"],
                date_format="%d/%m/%Y %H:%M"
            )
        return self._schedule_df

    def _get_current_stats(self) -> pd.DataFrame:
        """Fetch current team stats from NBA.com with caching"""
        # Cache stats for 10 minutes to avoid hammering NBA.com
        if hasattr(self, '_stats_cache') and hasattr(self, '_stats_cache_time'):
            cache_age = (get_current_datetime() - self._stats_cache_time).total_seconds()
            if cache_age < 600 and self._stats_cache is not None and not self._stats_cache.empty:
                print(f"[NBAPredictionService] Using cached stats ({int(cache_age)}s old)")
                return self._stats_cache
        
        try:
            print("[NBAPredictionService] Fetching fresh stats from NBA.com...")
            stats_json = get_json_data(DATA_URL)
            df = to_data_frame(stats_json)
            if not df.empty:
                self._stats_cache = df
                self._stats_cache_time = get_current_datetime()
                print(f"[NBAPredictionService] Cached stats for {len(df)} teams")
            return df
        except Exception as e:
            print(f"[NBAPredictionService] Stats fetch error: {e}")
            # Return cached data if available
            if hasattr(self, '_stats_cache') and self._stats_cache is not None:
                print("[NBAPredictionService] Using stale cache as fallback")
                return self._stats_cache
            return pd.DataFrame()

    def _get_odds(self) -> Optional[Dict]:
        """Fetch odds from sportsbook"""
        try:
            provider = SbrOddsProvider(sportsbook=self.sportsbook)
            odds = provider.get_odds()
            if odds and len(odds) > 0:
                return odds
            return None
        except Exception as e:
            print(f"[NBAPredictionService] Odds fetch failed: {e}")
            return None

    def _fetch_live_scores(self) -> Dict[str, Dict]:
        """
        Fetch live scores and game status from NBA.com mobile API.
        Returns dict keyed by 'Home:Away' with {status, home_score, away_score}
        """
        try:
            data = get_json_data(TODAYS_GAMES_URL)
            if not data: return {}
            
            games_map = {}
            # Traverse JSON structure: sports_content -> games -> game
            # This URL structure might vary, adapting to common NBA data structure
            # Structure: { gs: { g: [ ... ] } } or similar.
            # Using robust traversal if possible, or assuming standard v2015 format
            
            # Simplified parsing logic based on standard NBA data
            if 'gs' in data and 'g' in data['gs']:
                games = data['gs']['g']
                for game in games:
                    v_team = game.get('v', {}).get('ta') # Visiting Team Abbr
                    h_team = game.get('h', {}).get('ta') # Home Team Abbr
                    v_score = game.get('v', {}).get('s')
                    h_score = game.get('h', {}).get('s')
                    status_code = game.get('st') # 1=Scheduled, 2=Live, 3=Final
                    
                    status = 'SCHEDULED'
                    if status_code == 2: status = 'LIVE'
                    elif status_code == 3: status = 'FINAL'
                    
                    if v_team and h_team:
                        # Normalize team codes if necessary (e.g. UTH -> UTA)
                        # We'll assume standard codes match our index for now
                        key = f"{h_team}:{v_team}"
                        games_map[key] = {
                            'status': status,
                            'home_score': int(h_score) if h_score else 0,
                            'away_score': int(v_score) if v_score else 0
                        }
            return games_map
        except Exception as e:
            print(f"[NBAPredictionService] Live score fetch failed: {e}")
            return {}

    def _get_games_from_schedule(self, today: datetime) -> List[List[str]]:
        """
        Fallback: Get today's games from schedule CSV when odds scraper fails.
        Returns list of [home_team, away_team] pairs.
        
        The CSV has dates in UTC. NBA games typically start 7pm-10pm EST.
        7pm EST = 00:00 UTC next day
        10pm EST = 03:00 UTC next day
        
        So for "today's games" in EST, we need to look at:
        - Games on "tomorrow" in UTC (00:00-05:00 UTC = 7pm-midnight EST today)
        """
        try:
            schedule_df = self._load_schedule()
            
            # Get today's date in EST/NBA timezone
            today_date = today.date()
            
            # NBA games "today" in EST are typically scheduled as "tomorrow" in UTC
            # because 7pm EST = 00:00 UTC next day
            # So we look for games dated as tomorrow in UTC
            tomorrow_utc = today_date + timedelta(days=1)
            
            # Primary: Look for games on "tomorrow" UTC (which are tonight's games in EST)
            todays_games = schedule_df[
                schedule_df["Date"].dt.date == tomorrow_utc
            ]
            
            # Also include any late afternoon games that might be on "today" UTC
            # (games before 7pm EST would still be on "today" UTC)
            if todays_games.empty:
                todays_games = schedule_df[
                    schedule_df["Date"].dt.date == today_date
                ]
            
            games = []
            for _, row in todays_games.iterrows():
                home_team = row["Home Team"]
                away_team = row["Away Team"]
                location = row.get("Location", "")
                # Only include if both teams are in the current team index
                if home_team in team_index_current and away_team in team_index_current:
                    games.append([home_team, away_team, location])
            
            print(f"[NBAPredictionService] Found {len(games)} games from schedule for {today_date}")
            return games
            
        except Exception as e:
            print(f"[NBAPredictionService] Schedule read failed: {e}")
            return []

    def _resolve_games(self, odds: Optional[Dict], today: datetime = None) -> List[List[str]]:
        """Get today's games from odds, falling back to schedule CSV"""
        # Try odds-based games first
        if odds:
            games = create_todays_games_from_odds(odds)
            if games:
                print(f"[NBAPredictionService] Found {len(games)} games from odds")
                # Normalize to include None for location (will be looked up later)
                return [[g[0], g[1], None] for g in games]
        
        # Fallback to schedule CSV
        if today is None:
            today = get_current_datetime()
        return self._get_games_from_schedule(today)

    def _calculate_days_rest(
        self, team: str, schedule_df: pd.DataFrame, today: datetime
    ) -> int:
        """Calculate days of rest for a team"""
        team_games = schedule_df[
            (schedule_df["Home Team"] == team) | (schedule_df["Away Team"] == team)
        ]
        # Convert today to naive datetime for comparison with schedule dates
        today_naive = today.replace(tzinfo=None) if today.tzinfo else today
        previous_games = team_games.loc[
            team_games["Date"] <= today_naive
        ].sort_values("Date", ascending=False).head(1)["Date"]

        if len(previous_games) > 0:
            last_date = previous_games.iloc[0]
            # Convert pandas Timestamp to datetime if needed
            if hasattr(last_date, 'to_pydatetime'):
                last_date = last_date.to_pydatetime()
            # Use naive datetime for subtraction
            if hasattr(last_date, 'tzinfo') and last_date.tzinfo:
                last_date = last_date.replace(tzinfo=None)
            days_off = timedelta(days=1) + today_naive - last_date
            return days_off.days
        return 7  # Default if no previous games found

    def _prepare_game_data(
        self,
        games: List[List[str]],
        df: pd.DataFrame,
        odds: Optional[Dict],
        schedule_df: pd.DataFrame,
        today: datetime,
    ) -> tuple:
        """Prepare data matrices for prediction"""
        match_data = []
        todays_games_uo = []
        home_team_odds = []
        away_team_odds = []
        game_start_times = []  # track start times
        game_locations = []    # track locations (stadiums)

        for game in games:
            home_team, away_team, location = game
            if home_team not in team_index_current or away_team not in team_index_current:
                continue

            start_time = None
            
            # Get odds data and start time from odds
            if odds:
                game_key = f"{home_team}:{away_team}"
                if game_key in odds:
                    game_odds = odds[game_key]
                    todays_games_uo.append(game_odds.get("under_over_odds", 220))
                    home_team_odds.append(game_odds.get(home_team, {}).get("money_line_odds", 0))
                    away_team_odds.append(game_odds.get(away_team, {}).get("money_line_odds", 0))
                    start_time = game_odds.get("start_time")
                    # Capture Scores & Status if available (from SbrOddsProvider if implemented, or we'll inject it)
                    # Note: SbrOddsProvider might need update to return these, or we rely on main.py integration
                    # For now, we'll placeholder variables that will be passed out
                else:
                    todays_games_uo.append(220)
                    home_team_odds.append(0)
                    away_team_odds.append(0)
            else:
                todays_games_uo.append(220)
                home_team_odds.append(0)
                away_team_odds.append(0)
            
            # Fallback: get start time and location from schedule CSV if not available
            if not start_time or not location:
                try:
                    # Check both today and tomorrow (UTC vs EST difference)
                    target_dates = [today.date(), today.date() + timedelta(days=1)]
                    game_row = schedule_df[
                        (schedule_df["Home Team"] == home_team) & 
                        (schedule_df["Away Team"] == away_team) &
                        (schedule_df["Date"].dt.date.isin(target_dates))
                    ]
                    if not game_row.empty:
                        if not start_time:
                            start_time = game_row.iloc[0]["Date"].isoformat()
                            # Ensure UTC format so frontend converts to local time correctly
                            if start_time and not start_time.endswith('Z') and '+' not in start_time:
                                start_time += 'Z'
                        if not location:
                            location = game_row.iloc[0].get("Location", "")
                except Exception:
                    pass
            
            game_start_times.append(start_time)
            game_locations.append(location)

            # Calculate days rest
            home_days_off = self._calculate_days_rest(home_team, schedule_df, today)
            away_days_off = self._calculate_days_rest(away_team, schedule_df, today)

            # Get team stats
            home_team_series = df.iloc[team_index_current.get(home_team)]
            away_team_series = df.iloc[team_index_current.get(away_team)]
            stats = pd.concat([home_team_series, away_team_series])
            stats["Days-Rest-Home"] = home_days_off
            stats["Days-Rest-Away"] = away_days_off
            match_data.append(stats)

        if not match_data:
            return None, [], None, [], [], []

        games_data_frame = pd.concat(match_data, ignore_index=True, axis=1).T
        frame_ml = games_data_frame.drop(columns=["TEAM_ID", "TEAM_NAME"], errors="ignore")
        data = frame_ml.values.astype(float)

        return data, todays_games_uo, frame_ml, home_team_odds, away_team_odds, game_start_times, game_locations


    def _predict_for_date(
        self, 
        target_date: datetime,
        df: pd.DataFrame,
        schedule_df: pd.DataFrame,
        odds: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Generate predictions for a specific date.
        
        Args:
            target_date: The date to generate predictions for
            df: Current team stats DataFrame
            schedule_df: Schedule DataFrame
            odds: Odds dictionary (may only have today's odds)
            
        Returns:
            List of prediction dictionaries for that date
        """
        # Get games for this specific date from schedule
        games = self._get_games_from_schedule(target_date)
        
        if not games:
            return []
        
        # Prepare data for this date
        result = self._prepare_game_data(games, df, odds, schedule_df, target_date)
        if result[0] is None:
            return []
        
        data, games_uo, frame_ml, home_team_odds, away_team_odds, game_start_times, game_locations = result
        
        # Make predictions using XGBoost models
        ml_predictions = _predict_probs(
            XGBoost_Runner.xgb_ml, 
            data, 
            XGBoost_Runner.xgb_ml_calibrator
        )
        
        # Prepare Over/Under data
        frame_uo = frame_ml.copy()
        frame_uo["OU"] = np.asarray(games_uo, dtype=float)
        ou_predictions = _predict_probs(
            XGBoost_Runner.xgb_uo, 
            frame_uo.values.astype(float), 
            XGBoost_Runner.xgb_uo_calibrator
        )
        
        # Build predictions list
        predictions = []
        for idx, game in enumerate(games):
            if idx >= len(ml_predictions):
                continue
            
            home_team, away_team, _ = game
            home_prob = float(ml_predictions[idx][1])
            away_prob = float(ml_predictions[idx][0])
            winner = int(np.argmax(ml_predictions[idx]))
            under_over = int(np.argmax(ou_predictions[idx]))
            
            pred_dict = {
                "home_team": home_team,
                "away_team": away_team,
                "predicted_winner": home_team if winner == 1 else away_team,
                "home_win_probability": round(home_prob * 100, 2),
                "away_win_probability": round(away_prob * 100, 2),
                "winner_confidence": round(max(home_prob, away_prob) * 100, 2),
                "under_over_prediction": "UNDER" if under_over == 0 else "OVER",
                "under_over_line": float(games_uo[idx]) if idx < len(games_uo) else 0,
                "ou_confidence": round(float(ou_predictions[idx][under_over]) * 100, 2),
                "home_odds": int(home_team_odds[idx]) if idx < len(home_team_odds) and home_team_odds[idx] else 0,
                "away_odds": int(away_team_odds[idx]) if idx < len(away_team_odds) and away_team_odds[idx] else 0,
                "start_time_utc": game_start_times[idx] if idx < len(game_start_times) else None,
                "stadium": game_locations[idx] if idx < len(game_locations) else None,
                "timestamp": get_current_timestamp(),
            }

            # Merge with Live Score Data
            game_key = f"{home_team}:{away_team}"
            if hasattr(self, '_live_scores') and game_key in self._live_scores:
                score_data = self._live_scores[game_key]
                pred_dict["status"] = score_data.get("status", "SCHEDULED")
                pred_dict["home_score"] = score_data.get("home_score", 0)
                pred_dict["away_score"] = score_data.get("away_score", 0)
            else:
                pred_dict["status"] = "SCHEDULED"
            
            predictions.append(pred_dict)
        
        return predictions

    def get_todays_predictions(self) -> List[Dict[str, Any]]:
        """
        Get predictions for the next 3 days (today, tomorrow, day after).
        
        Returns:
            List of prediction dictionaries for all upcoming games.
        """
        return self.get_upcoming_predictions(days=3)

    def get_upcoming_predictions(self, days: int = 3) -> List[Dict[str, Any]]:
        """
        Get predictions for the next N days.
        
        Args:
            days: Number of days to predict (default 3)
            
        Returns:
            List of prediction dictionaries, sorted by start time.
        """
        # Ensure models are loaded
        if not self.models_loaded:
            if not self.load_models():
                return []
        
        try:
            # Load schedule once
            schedule_df = self._load_schedule()
            
            # Get current stats from NBA.com (same for all days)
            print("[NBAPredictionService] Fetching current stats from NBA.com...")
            df = self._get_current_stats()
            if df.empty:
                print("[NBAPredictionService] Could not fetch current stats from NBA.com - DataFrame is empty")
                return []
            print(f"[NBAPredictionService] Got stats for {len(df)} teams")
            
            # Fetch odds
            odds = self._silence_output(self._get_odds)

            # Fetch live scores once for all predictions
            self._live_scores = self._fetch_live_scores()
            print(f"[NBAPredictionService] Fetched live scores for {len(self._live_scores)} games")
            
            # Generate predictions for each date
            all_predictions = []
            today = get_current_datetime()
            
            for day_offset in range(days):
                target_date = today + timedelta(days=day_offset)
                day_predictions = self._predict_for_date(
                    target_date, df, schedule_df, odds
                )
                all_predictions.extend(day_predictions)
                print(f"[NBAPredictionService] Found {len(day_predictions)} games for {target_date.date()}")
            
            # Sort by start time (earliest first)
            all_predictions.sort(
                key=lambda x: x.get("start_time_utc") or "9999",
            )
            
            # Save predictions to database for history tracking
            if all_predictions:
                try:
                    save_predictions(all_predictions)
                except Exception as db_error:
                    print(f"[NBAPredictionService] DB save warning: {db_error}")
            
            print(f"[NBAPredictionService] Total: {len(all_predictions)} predictions for {days} days")
            return all_predictions
        
        except Exception as e:
            print(f"[NBAPredictionService] Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return []


# Singleton instance for API usage
_service_instance: Optional[NBAPredictionService] = None


def reset_service():
    """Reset the singleton service (for testing/reloading)"""
    global _service_instance
    _service_instance = None


def get_prediction_service(sportsbook: str = "fanduel") -> NBAPredictionService:
    """Get or create singleton prediction service"""
    global _service_instance
    if _service_instance is None:
        print("[NBAPredictionService] Creating new service instance...")
        _service_instance = NBAPredictionService(sportsbook=sportsbook)
        success = _service_instance.load_models()
        if not success:
            print("[NBAPredictionService] WARNING: Models failed to load")
    return _service_instance

