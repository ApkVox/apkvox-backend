"""
NBA Prediction Service Wrapper

Isolates the nba_engine prediction logic from the CLI interface,
providing a clean API for FastAPI integration.
"""

import sys
import io
import contextlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
# Import AI Researcher
try:
    from ai_researcher import SportsInvestigator
except ImportError:
    SportsInvestigator = None

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
from src.Utils.FeatureEngine import FeatureEngine
TODAYS_GAMES_URL = "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2025/scores/00_todays_scores.json"
DATA_URL = "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGames=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2025-26&SeasonSegment=&SeasonType=Regular%20Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="
DATA_URL_TEN = "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGames=10&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2025-26&SeasonSegment=&SeasonType=Regular%20Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="
DATA_URL_ADV = "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGames=0&LeagueID=00&Location=&MeasureType=Advanced&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2025-26&SeasonSegment=&SeasonType=Regular%20Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="
DATA_URL_ADV_TEN = "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGames=10&LeagueID=00&Location=&MeasureType=Advanced&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2025-26&SeasonSegment=&SeasonType=Regular%20Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="
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
        
        # PERFORMANCE: AI Investigator disabled by default (adds 4+ network calls per game)
        # To re-enable: set self.investigator = SportsInvestigator() if SportsInvestigator else None
        self.investigator = None
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
            print("[NBAPredictionService] Fetching fresh stats from NBA.com (parallel)...")
            # PERFORMANCE: Fetch all 4 stats endpoints in parallel
            urls = {
                'base': DATA_URL,
                'ten': DATA_URL_TEN,
                'adv': DATA_URL_ADV,
                'adv_ten': DATA_URL_ADV_TEN
            }
            results = {}
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(get_json_data, url): key for key, url in urls.items()}
                for future in as_completed(futures):
                    key = futures[future]
                    try:
                        results[key] = future.result()
                    except Exception as e:
                        print(f"[NBAPredictionService] Failed to fetch {key}: {e}")
                        results[key] = None
            
            stats_json = results.get('base')
            stats_json_ten = results.get('ten')
            stats_json_adv = results.get('adv')
            stats_json_adv_ten = results.get('adv_ten')
            
            df = to_data_frame(stats_json)
            df_ten = to_data_frame(stats_json_ten)
            df_adv = to_data_frame(stats_json_adv)
            df_adv_ten = to_data_frame(stats_json_adv_ten)
            
            if not df.empty and not df_ten.empty:
                # Merge base stats
                df_ten = df_ten.add_suffix("_L10")
                
                if "TEAM_ID" in df.columns and "TEAM_ID_L10" in df_ten.columns:
                     df_combined = pd.merge(df, df_ten, left_on="TEAM_ID", right_on="TEAM_ID_L10", how="inner")
                else:
                    df_combined = pd.concat([df, df_ten], axis=1)
                
                # Merge advanced stats if available
                if not df_adv.empty:
                    df_adv = df_adv.add_suffix("_ADV")
                    if "TEAM_ID_ADV" in df_adv.columns:
                        df_combined = pd.merge(df_combined, df_adv, left_on="TEAM_ID", right_on="TEAM_ID_ADV", how="inner")
                    else:
                        df_combined = pd.concat([df_combined, df_adv], axis=1)
                
                if not df_adv_ten.empty:
                    df_adv_ten = df_adv_ten.add_suffix("_ADV_L10")
                    if "TEAM_ID_ADV_L10" in df_adv_ten.columns:
                        df_combined = pd.merge(df_combined, df_adv_ten, left_on="TEAM_ID", right_on="TEAM_ID_ADV_L10", how="inner")
                    else:
                        df_combined = pd.concat([df_combined, df_adv_ten], axis=1)

                self._stats_cache = df_combined
                self._stats_cache_time = get_current_datetime()
                print(f"[NBAPredictionService] Cached stats for {len(df_combined)} teams (Season + L10 + ADV)")
            return self._stats_cache if hasattr(self, '_stats_cache') else pd.DataFrame()
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
        Get games from schedule CSV for a specific target date.
        Returns list of [home_team, away_team, location] triples.
        
        The CSV has dates in UTC. NBA games typically start 7pm-10pm EST.
        7pm EST = 00:00 UTC next day
        10pm EST = 03:00 UTC next day
        
        To capture all games for an "NBA day" (which spans two UTC calendar days),
        we check BOTH the target date AND the next day in UTC.
        """
        try:
            schedule_df = self._load_schedule()
            
            # Get target date
            target_date = today.date()
            # Strict Filtering: Adjust UTC schedule to NBA time (approx -6h offset)
            # This prevents overlap between days and properly aligns games to their local "NBA Day"
            # Vectorized operation for efficiency
            nba_time = schedule_df["Date"] - timedelta(hours=6)
            todays_games = schedule_df[
                nba_time.dt.date == target_date
            ]
            
            games = []
            for _, row in todays_games.iterrows():
                home_team = row["Home Team"]
                away_team = row["Away Team"]
                location = row.get("Location", "")
                # Only include if both teams are in the current team index
                if home_team in team_index_current and away_team in team_index_current:
                    games.append([home_team, away_team, location])
            
            print(f"[NBAPredictionService] Found {len(games)} games from schedule for {target_date}")
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
            # Stats dataframe now has Season columns AND _L10 columns
            # match_data expectations: 
            # Season Home, Season Away, Season Home L10, Season Away L10 ??
            # Wait, `Create_Games.py` does:
            # 1. Home Season
            # 2. Home L10
            # 3. Away Season
            # 4. Away L10
            
            # Predictor logic MUST MATCH this order.
            
            # Locate team rows using team_index_current map to index
            # Warning: df is now the combined dataframe.
            
            # We need to extract the specific blocks.
            # Assuming df columns are [Season Cols] + [L10 Cols] due to the merge.
            
            # It's cleaner to construct the series by name lookup if possible, but the code uses iloc.
            # Let's trust that team_index_current maps to the correct rows in the combined DF 
            # (which comes from merging sorted NBA API responses, usually alphabetical/ID sorted).
            
            # However, the merged DF columns are mixed.
            # We need to reconstruct the EXACT vector structure:
            
            # X = [Home_Season, Home_L10, Away_Season, Away_L10]
            
            # Let's verify columns.
            # df has keys like 'PTS', 'REB', ... 'PTS_L10', 'REB_L10'
            
            # We need to separate them.
            season_cols = [c for c in df.columns if not c.endswith('_L10')]
            l10_cols = [c for c in df.columns if c.endswith('_L10')]
            
            # Get specific team rows
            # Note: iloc works on rows, but we need to slice columns too
            
            home_row = df.iloc[team_index_current.get(home_team)]
            away_row = df.iloc[team_index_current.get(away_team)]
            
            home_season = home_row[season_cols]
            home_l10 = home_row[l10_cols]
            
            away_season = away_row[season_cols]
            away_l10 = away_row[l10_cols]
            
            # Rename for concatenation (replicating Create_Games structure)
            # Create_Games: away_season.rename(index={col: f"{col}.1"...})
            
            stats = pd.concat([
                home_season,
                home_l10,
                away_season.rename(index={col: f"{col}.1" for col in season_cols}),
                away_l10.rename(index={col: f"{col}.1" for col in l10_cols}).add_suffix("_L10") # Hacky: it already has _L10, so it becomes _L10.1?
                # Actually, Create_Games: 
                # away_l10.rename(index={col: f"{col}.1" for col in l10_df.columns.values}).add_suffix("_L10")
                # Wait, l10_df columns in Create_Games are RAW, then adds suffix _L10.
                
                # Here `away_l10` ALREADY has `_L10` suffix.
                # So we just need to add `.1` to them.
            ])
            
            # Correction:
            # Create_Games:: 
            # home_l10 = l10_df.iloc[home_index].add_suffix("_L10")
            # away_l10 = l10_df.iloc[away_index].add_suffix("_L10")
            # return pd.concat([
            #    home_season,
            #    home_l10,
            #    away_season.rename(index={col: f"{col}.1" ...}),
            #    away_l10.rename(index={col: f"{col}.1" ...}).add_suffix("_L10")
            # ])
            
            # Wait, away_l10 in create_games is derived from `l10_df` (raw).
            # So `away_l10` in Create_Games ALREADY has `_L10` suffix before the LAST rename line?
            # No:
            # home_l10 = l10_df...add_suffix("_L10") -> cols become "PTS_L10"
            # away_l10 = l10_df...add_suffix("_L10") -> cols become "PTS_L10"
            
            # Then concat:
            # away_l10.rename(...).add_suffix("_L10") ??
            # The line in Create_Games was:
            # away_l10.rename(index={col: f"{col}.1" for col in l10_df.columns.values}).add_suffix("_L10")
            
            # `l10_df.columns.values` are RAW names (PTS).
            # So map is PTS -> PTS.1
            # But away_l10 index is ALREADY PTS_L10.
            # So the rename map key 'PTS' won't match 'PTS_L10'.
            # That logic in Create_Games might be slightly buggy or I misread it. 
            
            # Let's re-read the Create_Games edit I made.
            # away_l10 = l10_df.iloc[away_index].add_suffix("_L10")  <-- Index is PTS_L10
            # concat element: away_l10.rename(index={col: f"{col}.1" for col in l10_df.columns.values}).add_suffix("_L10")
            
            # If I rename 'PTS' -> 'PTS.1', but index is 'PTS_L10', it ignores it.
            # Then .add_suffix("_L10") makes it 'PTS_L10_L10'. This looks WRONG in my Create_Games logic.
            
            # CORRECT LOGIC in Create_Games should be:
            # away_raw = l10_df.iloc[away_index]
            # normalized_away_l10 = away_raw.rename(index={col: f"{col}.1" for col in raw_columns}).add_suffix("_L10")
            # Result: PTS.1_L10
            
            # Let's fix Predictor to do what makes sense, and I might need to hotfix Create_Games if I messed it up.
            # Standard feature vector usually:
            # [Home_PTS, ..., Home_PTS_L10, ..., Away_PTS.1, ..., Away_PTS.1_L10]
            
            # My Create_Games edit:
            # away_l10 = l10_df.iloc[away_index].add_suffix("_L10") (PTS_L10)
            # Element 4: away_l10.rename(index={col: f"{col}.1" for col in l10_df.columns.values}).add_suffix("_L10")
            # Since rename keys don't match index, it does nothing? No, rename ignores missing keys.
            # Then add_suffix gets applied. Result: PTS_L10_L10.
            
            # That is definitely redundant.
            
            # I will assume the target vector schema is:
            # H_Season (PTS)
            # H_L10 (PTS_L10)
            # A_Season (PTS.1)
            # A_L10 (PTS.1_L10)
            
            # Separate columns by type
            season_cols = [c for c in df.columns if not c.endswith('_L10') and not c.endswith('_ADV') and not c.endswith('_ADV_L10')]
            l10_cols = [c for c in df.columns if c.endswith('_L10') and not c.endswith('_ADV_L10')]
            adv_cols = [c for c in df.columns if c.endswith('_ADV') and not c.endswith('_ADV_L10')]
            adv_l10_cols = [c for c in df.columns if c.endswith('_ADV_L10')]
            
            home_season = home_row[season_cols]
            home_l10 = home_row[l10_cols]
            
            away_season = away_row[season_cols].rename(index=lambda x: f"{x}.1")
            away_l10 = away_row[l10_cols].rename(index=lambda x: x.replace("_L10", ".1_L10"))
            
            # Calculate efficiency metrics (matching Create_Games)
            home_eff = FeatureEngine.calculate_efficiency_metrics(home_season)
            home_l10_eff = FeatureEngine.calculate_efficiency_metrics(home_row[l10_cols]).add_suffix("_L10")
            away_eff = FeatureEngine.calculate_efficiency_metrics(away_row[season_cols]).rename(index=lambda x: f"{x}.1")
            away_l10_eff = FeatureEngine.calculate_efficiency_metrics(away_row[l10_cols]).rename(index=lambda x: f"{x}.1_L10")
            
            # Build feature list matching Create_Games order:
            # home_season, home_l10, home_eff, home_l10_eff
            # away_season, away_l10, away_eff, away_l10_eff
            # Note: We are IGNORING inferred ADV columns because the model was trained without them
            # (since historical data doesn't have them yet).
            features = [home_season, home_l10, home_eff, home_l10_eff]
            
            # if adv_cols: ... (Disabled to match training)
            
            features.extend([away_season, away_l10, away_eff, away_l10_eff])
            
            # if adv_cols: ... (Disabled to match training)
            
            stats = pd.concat(features)
            stats["Days-Rest-Home"] = home_days_off
            stats["Days-Rest-Away"] = away_days_off
            match_data.append(stats)

        if not match_data:
            return None, [], None, [], [], []

        games_data_frame = pd.concat(match_data, ignore_index=True, axis=1).T
        
        # Drop all non-numeric columns (IDs, Names, Dates) including L10 and ADV variants
        cols_to_drop = [
            "TEAM_ID", "TEAM_ID.1", "TEAM_ID_L10", "TEAM_ID.1_L10",
            "TEAM_ID_ADV", "TEAM_ID.1_ADV", "TEAM_ID_ADV_L10", "TEAM_ID.1_ADV_L10",
            "TEAM_NAME", "TEAM_NAME.1", "TEAM_NAME_L10", "TEAM_NAME.1_L10",
            "TEAM_NAME_ADV", "TEAM_NAME.1_ADV", "TEAM_NAME_ADV_L10", "TEAM_NAME.1_ADV_L10",
            "Date_L10", "Date.1_L10", "Date_ADV", "Date.1_ADV", "Date_ADV_L10", "Date.1_ADV_L10"
        ]
        frame_ml = games_data_frame.drop(columns=cols_to_drop, errors="ignore")
        # Enforce alphabetical feature order to match training
        frame_ml = frame_ml.reindex(sorted(frame_ml.columns), axis=1)
        print(f"[DEBUG] Predictor frame shape: {frame_ml.shape}")
        # print(f"[DEBUG] Predictor columns: {frame_ml.columns.tolist()}")
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
            
            # --- AI INVESTIGATION LAYER (CACHE-BASED) ---
            # Read pre-computed insights from database cache (instant)
            # Background worker (ai_worker.py) populates this cache
            from .database import get_ai_insight
            
            ai_data = {"summary": "Análisis pendiente", "impact_score": 0.0, "key_factors": [], "confidence": 0}
            game_date = str(target_date.date())
            
            try:
                # Get cached insights for both teams
                h_insight = get_ai_insight(home_team, game_date)
                a_insight = get_ai_insight(away_team, game_date)
                
                if h_insight or a_insight:
                    h_score = h_insight.get("impact_score", 0) if h_insight else 0
                    a_score = a_insight.get("impact_score", 0) if a_insight else 0
                    net_impact = h_score - a_score
                    
                    h_summary = h_insight.get("summary", "Sin datos") if h_insight else "Sin datos"
                    a_summary = a_insight.get("summary", "Sin datos") if a_insight else "Sin datos"
                    
                    h_factors = h_insight.get("key_factors", []) if h_insight else []
                    a_factors = a_insight.get("key_factors", []) if a_insight else []
                    
                    h_conf = h_insight.get("confidence", 0) if h_insight else 0
                    a_conf = a_insight.get("confidence", 0) if a_insight else 0
                    
                    ai_data = {
                        "summary": f"Home: {h_summary} | Away: {a_summary}",
                        "impact_score": net_impact,
                        "key_factors": h_factors + a_factors,
                        "confidence": (h_conf + a_conf) / 2 if (h_conf or a_conf) else 0
                    }
            except Exception as e:
                print(f"  [AI Cache] Error reading cache: {e}")

            pred_dict = {
                "home_team": home_team,
                "away_team": away_team,
                "ai_impact": ai_data,
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
            
            # --- SMART BETTING LOGIC ---
            # Convert Odds
            h_odds_dec = 1.0
            a_odds_dec = 1.0
            
            # Helper to convert American to Decimal
            def to_decimal(us_odds):
                try:
                    o = float(us_odds)
                    if o > 0: return (o / 100) + 1
                    else: return (100 / abs(o)) + 1
                except: return 1.0

            if home_team_odds[idx]: h_odds_dec = to_decimal(home_team_odds[idx])
            if away_team_odds[idx]: a_odds_dec = to_decimal(away_team_odds[idx])

            # Calculate Edge (MyProb - ImpliedProb)
            h_implied = 1 / h_odds_dec if h_odds_dec > 0 else 1
            a_implied = 1 / a_odds_dec if a_odds_dec > 0 else 1
            
            h_edge = home_prob - h_implied
            a_edge = away_prob - a_implied
            
            # Decision Rule: >10% Edge AND >1.50 Odds
            MIN_ODDS = 1.50
            MIN_EDGE = 0.10
            
            recommendation = "SKIP"
            rec_unit = 0
            
            if winner == 1: # Pred Home
                if h_edge > MIN_EDGE and h_odds_dec >= MIN_ODDS:
                    recommendation = "BET HOME"
                    rec_unit = 1 
                    # AI Veto
                    if ai_data.get("impact_score", 0) < -3.0:
                         recommendation = "SKIP (AI RISK)"
                         rec_unit = 0

            else: # Pred Away
                if a_edge > MIN_EDGE and a_odds_dec >= MIN_ODDS:
                    recommendation = "BET AWAY"
                    rec_unit = 1
                    # AI Veto
                    # Positive score favors Home, so we want Negative score for Away.
                    # If score is > +3.0, it means Home is favored by news (bad for Away bet)
                    if ai_data.get("impact_score", 0) > 3.0:
                         recommendation = "SKIP (AI RISK)"
                         rec_unit = 0

            pred_dict["recommendation"] = recommendation
            pred_dict["edge_percent"] = round(max(h_edge, a_edge) * 100, 1)
            pred_dict["ev_home"] = round((home_prob * h_odds_dec) - 1, 2)
            pred_dict["ev_away"] = round((away_prob * a_odds_dec) - 1, 2)
            
            predictions.append(pred_dict)
        
        return predictions

    def get_todays_predictions(self) -> List[Dict[str, Any]]:
        """
        Get predictions for today only (fast default).
        
        Returns:
            List of prediction dictionaries for today's games.
        """
        return self.get_upcoming_predictions(days=1)

    def get_upcoming_predictions(self, days: int = 3, target_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get predictions for the next N days OR a specific target date.
        
        Args:
            days: Number of days to predict (default 3)
            target_date: Specific date to predict for (overrides days)
            
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
            
            dates_to_process = []
            if target_date:
                dates_to_process.append(target_date)
            else:
                today = get_current_datetime()
                for day_offset in range(days):
                    dates_to_process.append(today + timedelta(days=day_offset))
            
            for current_date in dates_to_process:
                day_predictions = self._predict_for_date(
                    current_date, df, schedule_df, odds
                )
                all_predictions.extend(day_predictions)
                print(f"[NBAPredictionService] Found {len(day_predictions)} games for {current_date.date()}")
            
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

