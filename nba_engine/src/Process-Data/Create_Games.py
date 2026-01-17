import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import toml
import sys
import os

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(1, os.fspath(BASE_DIR))

from src.Utils.Dictionaries import (
    team_index_07,
    team_index_08,
    team_index_12,
    team_index_13,
    team_index_14,
    team_index_current,
)

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config.toml"
ODDS_DB_PATH = BASE_DIR / "Data" / "OddsData.sqlite"
TEAMS_DB_PATH = BASE_DIR / "Data" / "TeamData.sqlite"
OUTPUT_DB_PATH = BASE_DIR / "Data" / "dataset.sqlite"
OUTPUT_TABLE = "dataset_2012-26"

TEAM_INDEX_BY_SEASON = {
    "2007-08": team_index_07,
    "2008-09": team_index_08,
    "2009-10": team_index_08,
    "2010-11": team_index_08,
    "2011-12": team_index_08,
    "2012-13": team_index_12,
    "2013-14": team_index_13,
    "2014-15": team_index_14,
    "2015-16": team_index_14,
    "2016-17": team_index_14,
    "2017-18": team_index_14,
    "2018-19": team_index_14,
    "2019-20": team_index_14,
    "2020-21": team_index_14,
    "2021-22": team_index_14,
    "2022-23": team_index_current,
    "2023-24": team_index_current,
    "2024-25": team_index_current,
    "2025-26": team_index_current,
}


def table_exists(con, table_name):
    cursor = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def normalize_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if hasattr(value, "date"):
        try:
            return value.date().isoformat()
        except Exception:
            pass
    return str(value)


def get_team_index_map(season_key):
    if season_key in TEAM_INDEX_BY_SEASON:
        return TEAM_INDEX_BY_SEASON[season_key]
    try:
        start_year = int(season_key.split("-")[0])
    except (ValueError, IndexError):
        return team_index_current
    return team_index_current if start_year >= 2022 else team_index_14


def fetch_team_table(teams_con, date_str):
    if not table_exists(teams_con, date_str):
        return None
    return pd.read_sql_query(f'SELECT * FROM "{date_str}"', teams_con)


def calculate_efficiency_metrics(row):
    """
    Calculate efficiency metrics from base stats.
    Returns a Series with calculated metrics.
    
    Metrics calculated:
    - TS_PCT: True Shooting % = PTS / (2 * (FGA + 0.44 * FTA))
    - EFG_PCT: Effective FG% = (FGM + 0.5 * FG3M) / FGA
    - AST_TOV: Assist/Turnover Ratio = AST / TOV
    - PACE_EST: Estimated Pace = FGA + 0.44 * FTA - OREB + TOV
    - OFF_EFF: Offensive Efficiency = PTS / PACE_EST * 100
    """
    try:
        pts = float(row.get('PTS', 0))
        fga = float(row.get('FGA', 1))  # Avoid div by zero
        fta = float(row.get('FTA', 0))
        fgm = float(row.get('FGM', 0))
        fg3m = float(row.get('FG3M', 0))
        ast = float(row.get('AST', 0))
        tov = float(row.get('TOV', 1))  # Avoid div by zero
        oreb = float(row.get('OREB', 0))
        
        # True Shooting Percentage
        ts_attempts = 2 * (fga + 0.44 * fta)
        ts_pct = pts / ts_attempts if ts_attempts > 0 else 0
        
        # Effective Field Goal Percentage
        efg_pct = (fgm + 0.5 * fg3m) / fga if fga > 0 else 0
        
        # Assist/Turnover Ratio
        ast_tov = ast / tov if tov > 0 else ast
        
        # Estimated Pace (possessions per game estimate)
        pace_est = fga + 0.44 * fta - oreb + tov
        
        # Offensive Efficiency (points per 100 possessions estimate)
        off_eff = (pts / pace_est * 100) if pace_est > 0 else 0
        
        return pd.Series({
            'TS_PCT': ts_pct,
            'EFG_PCT': efg_pct,
            'AST_TOV': ast_tov,
            'PACE_EST': pace_est,
            'OFF_EFF': off_eff
        })
    except Exception:
        return pd.Series({
            'TS_PCT': 0,
            'EFG_PCT': 0,
            'AST_TOV': 0,
            'PACE_EST': 0,
            'OFF_EFF': 0
        })


def build_game_features(team_df, l10_df, adv_df, adv_l10_df, home_team, away_team, index_map):
    home_index = index_map.get(home_team)
    away_index = index_map.get(away_team)
    if home_index is None or away_index is None:
        return None
    if len(team_df.index) != 30 or len(l10_df.index) != 30:
        return None
    # Advanced tables might not exist for all dates
    has_adv = adv_df is not None and len(adv_df.index) == 30
    has_adv_l10 = adv_l10_df is not None and len(adv_l10_df.index) == 30

    # Season stats
    home_season = team_df.iloc[home_index]
    away_season = team_df.iloc[away_index]
    
    # L10 stats (rename columns)
    home_l10 = l10_df.iloc[home_index].add_suffix("_L10")
    away_l10 = l10_df.iloc[away_index].add_suffix("_L10")
    
    # Calculate efficiency metrics using Unified FeatureEngine
    from src.Utils.FeatureEngine import FeatureEngine
    
    # Calculate efficiency metrics from base stats (no API needed!)
    home_eff = FeatureEngine.calculate_efficiency_metrics(home_season)
    home_l10_eff = FeatureEngine.calculate_efficiency_metrics(l10_df.iloc[home_index]).add_suffix("_L10")
    away_eff = FeatureEngine.calculate_efficiency_metrics(away_season).rename(index=lambda x: f"{x}.1")
    away_l10_eff = FeatureEngine.calculate_efficiency_metrics(l10_df.iloc[away_index]).rename(index=lambda x: f"{x}.1_L10")

    # Build feature list
    features = [
        home_season,
        home_l10,
        home_eff,           # Calculated efficiency for home team (season)
        home_l10_eff,       # Calculated efficiency for home team (L10)
    ]
    
    # Add API-fetched advanced metrics if available (optional bonus)
    if has_adv:
        home_adv = adv_df.iloc[home_index].add_suffix("_ADV")
        features.append(home_adv)
    if has_adv_l10:
        home_adv_l10 = adv_l10_df.iloc[home_index].add_suffix("_ADV_L10")
        features.append(home_adv_l10)
    
    # Away team
    features.append(away_season.rename(index={col: f"{col}.1" for col in team_df.columns.values}))
    features.append(away_l10.rename(index=lambda x: x.replace("_L10", ".1_L10")))
    features.append(away_eff)       # Calculated efficiency for away team (season)
    features.append(away_l10_eff)   # Calculated efficiency for away team (L10)
    
    if has_adv:
        away_adv = adv_df.iloc[away_index].add_suffix(".1_ADV")
        features.append(away_adv)
    if has_adv_l10:
        away_adv_l10 = adv_l10_df.iloc[away_index].add_suffix(".1_ADV_L10")
        features.append(away_adv_l10)
    
    return pd.concat(features)


def select_odds_table(odds_con, season_key):
    candidates = [
        f"odds_{season_key}_new",
        f"odds_{season_key}",
        f"{season_key}_new",
        f"{season_key}",
    ]
    for table_name in candidates:
        if table_exists(odds_con, table_name):
            return table_name
    return None


def fetch_l10_table(teams_con, date_str):
    table_name = f"{date_str}_L10"
    if not table_exists(teams_con, table_name):
        return None
    return pd.read_sql_query(f'SELECT * FROM "{table_name}"', teams_con)


def fetch_adv_table(teams_con, date_str):
    table_name = f"{date_str}_ADV"
    if not table_exists(teams_con, table_name):
        return None
    return pd.read_sql_query(f'SELECT * FROM "{table_name}"', teams_con)


def fetch_adv_l10_table(teams_con, date_str):
    table_name = f"{date_str}_ADV_L10"
    if not table_exists(teams_con, table_name):
        return None
    return pd.read_sql_query(f'SELECT * FROM "{table_name}"', teams_con)


def main():
    config = toml.load(CONFIG_PATH)

    scores = []
    win_margin = []
    ou_values = []
    ou_cover = []
    games = []
    days_rest_away = []
    days_rest_home = []

    with sqlite3.connect(ODDS_DB_PATH) as odds_con, sqlite3.connect(TEAMS_DB_PATH) as teams_con:
        for season_key in config["create-games"].keys():
        # for season_key in ["2025-26"]:
            print(season_key)
            odds_table = select_odds_table(odds_con, season_key)
            if not odds_table:
                print(f"Missing odds tables for {season_key}.")
                continue

            odds_df = pd.read_sql_query(f'SELECT * FROM "{odds_table}"', odds_con)
            if odds_df.empty:
                print(f"No odds data for {season_key}.")
                continue

            index_map = get_team_index_map(season_key)

            for row in odds_df.itertuples(index=False):
                # FIX DATA LEAKAGE: Use stats from the DAY BEFORE the game
                game_date_str = normalize_date(row.Date)
                try:
                    game_dt = datetime.strptime(game_date_str, "%Y-%m-%d")
                except ValueError: # Handle variations if normalize_date fails or returns unexpected format
                     # Attempt to parse standard formats
                     game_dt = datetime.strptime(str(row.Date).split()[0], "%Y-%m-%d")
                
                prev_dt = game_dt - timedelta(days=1)
                date_str = prev_dt.strftime("%Y-%m-%d") # Use THIS for fetching stats
                team_df = fetch_team_table(teams_con, date_str)
                l10_df = fetch_l10_table(teams_con, date_str)
                adv_df = fetch_adv_table(teams_con, date_str)
                adv_l10_df = fetch_adv_l10_table(teams_con, date_str)
                
                if team_df is None or l10_df is None:
                    continue

                game = build_game_features(team_df, l10_df, adv_df, adv_l10_df, row.Home, row.Away, index_map)
                if game is None:
                    continue

                scores.append(row.Points)
                ou_values.append(row.OU)
                days_rest_home.append(row.Days_Rest_Home)
                days_rest_away.append(row.Days_Rest_Away)
                win_margin.append(1 if row.Win_Margin > 0 else 0)

                if row.Points < row.OU:
                    ou_cover.append(0)
                elif row.Points > row.OU:
                    ou_cover.append(1)
                else:
                    ou_cover.append(2)

                games.append(game)

    if not games:
        print("No game rows produced. Check odds and team tables.")
        return

    season = pd.concat(games, ignore_index=True, axis=1).T
    
    # Drop all ID and Date columns (including L10 and ADV variants)
    cols_to_drop = [
        "TEAM_ID", "TEAM_ID.1", 
        "TEAM_ID_L10", "TEAM_ID.1_L10",
        "TEAM_ID_ADV", "TEAM_ID.1_ADV",
        "TEAM_ID_ADV_L10", "TEAM_ID.1_ADV_L10",
        "Date_L10", "Date.1_L10",
        "Date_ADV", "Date.1_ADV",
        "Date_ADV_L10", "Date.1_ADV_L10",
        "TEAM_NAME_L10", "TEAM_NAME.1_L10",
        "TEAM_NAME_ADV", "TEAM_NAME.1_ADV",
        "TEAM_NAME_ADV_L10", "TEAM_NAME.1_ADV_L10"
    ]
    frame = season.drop(columns=cols_to_drop, errors="ignore")
    frame["Score"] = np.asarray(scores)
    frame["Home-Team-Win"] = np.asarray(win_margin)
    frame["OU"] = np.asarray(ou_values)
    frame["OU-Cover"] = np.asarray(ou_cover)
    frame["Days-Rest-Home"] = np.asarray(days_rest_home)
    frame["Days-Rest-Away"] = np.asarray(days_rest_away)

    for field in frame.columns.values:
        if "TEAM_" in field or "Date" in field:
            continue
        frame[field] = frame[field].astype(float)

    with sqlite3.connect(OUTPUT_DB_PATH) as con:
        frame.to_sql(OUTPUT_TABLE, con, if_exists="replace", index=False)


if __name__ == "__main__":
    main()
