import argparse
import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import toml

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(1, os.fspath(BASE_DIR))

from src.Utils.tools import get_json_data, to_data_frame  # noqa: E402

CONFIG_PATH = BASE_DIR / "config.toml"
DB_PATH = BASE_DIR / "Data" / "TeamData.sqlite"
MIN_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 3
MAX_RETRIES = 3


def load_config():
    return toml.load(CONFIG_PATH)


def iter_dates(start_date, end_date):
    date_pointer = start_date
    while date_pointer <= end_date:
        yield date_pointer
        date_pointer += timedelta(days=1)


def select_current_season(config, today):
    for season_key, value in config["get-data"].items():
        start_date = datetime.strptime(value["start_date"], "%Y-%m-%d").date()
        end_date = datetime.strptime(value["end_date"], "%Y-%m-%d").date()
        if start_date <= today <= end_date:
            return season_key, value, start_date, end_date
    return None, None, None, None


def get_table_dates(con):
    season_dates = set()
    l10_dates = set()
    cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (name,) in cursor.fetchall():
        try:
            # Check for L10 first
            if name.endswith("_L10"):
                date_str = name.replace("_L10", "")
                l10_dates.add(datetime.strptime(date_str, "%Y-%m-%d").date())
            else:
                season_dates.add(datetime.strptime(name, "%Y-%m-%d").date())
        except ValueError:
            continue
    return season_dates, l10_dates


def fetch_data(url, date_pointer, start_year, season_key):
    for attempt in range(1, MAX_RETRIES + 1):
        raw_data = get_json_data(
            url.format(date_pointer.month, date_pointer.day, start_year, date_pointer.year, season_key)
        )
        df = to_data_frame(raw_data)
        if not df.empty:
            return df
        if attempt < MAX_RETRIES:
            time.sleep(MIN_DELAY_SECONDS + random.random() * (MAX_DELAY_SECONDS - MIN_DELAY_SECONDS))
    return pd.DataFrame(data={})


def backfill_season(con, url, url_ten, season_key, value, existing_dates, existing_l10_dates, today):
    start_date = datetime.strptime(value["start_date"], "%Y-%m-%d").date()
    end_date = datetime.strptime(value["end_date"], "%Y-%m-%d").date()
    fetch_end = min(today - timedelta(days=1), end_date)
    
    # We need to fetch if EITHER Season OR L10 is missing
    missing_dates = []
    for date_pointer in iter_dates(start_date, fetch_end):
        if date_pointer not in existing_dates or date_pointer not in existing_l10_dates:
            missing_dates.append(date_pointer)

    if not missing_dates:
        print(f"No missing dates for season {season_key}.")
        return

    print(f"Backfilling {len(missing_dates)} dates for season {season_key}.")
    for date_pointer in missing_dates:
        print("Getting data based on missing check:", date_pointer)
        
        # 1. Fetch Season Data if missing
        if date_pointer not in existing_dates:
            df = fetch_data(url, date_pointer, value["start_year"], season_key)
            if not df.empty:
                table_name = date_pointer.strftime("%Y-%m-%d")
                df["Date"] = table_name
                df.to_sql(table_name, con, if_exists="replace", index=False)
                existing_dates.add(date_pointer)
            else:
                print("No data returned for:", date_pointer)

        # 2. Fetch L10 Data if missing
        if date_pointer not in existing_l10_dates:
            df_ten = fetch_data(url_ten, date_pointer, value["start_year"], season_key)
            if not df_ten.empty:
                table_name_ten = date_pointer.strftime("%Y-%m-%d") + "_L10"
                df_ten["Date"] = table_name_ten
                df_ten.to_sql(table_name_ten, con, if_exists="replace", index=False)
                existing_l10_dates.add(date_pointer)
            else:
                print("No L10 data returned for:", date_pointer)



        time.sleep(random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

        # TODO: Add tests


def main(config=None, db_path=DB_PATH, today=None, backfill=False, season=None):
    if config is None:
        config = load_config()
    url = config["data_url"]
    url_ten = config["data_url_ten"]
    url_adv = config["data_url_adv"]
    url_adv_ten = config["data_url_adv_ten"]
    if today is None:
        today = datetime.today().date()

    with sqlite3.connect(db_path) as con:
        existing_dates, existing_l10_dates = get_table_dates(con)
        if backfill:
            season_items = config["get-data"].items()
            if season:
                season_items = [
                    (key, value) for key, value in season_items if key == season
                ]
                if not season_items:
                    print("Season not found in config:", season)
                    return

            for season_key, value in season_items:
                backfill_season(con, url, url_ten, season_key, value, existing_dates, existing_l10_dates, today)
            return

        season_key, value, start_date, end_date = select_current_season(config, today)
        if not season_key:
            print("No current season found for today:", today)
            return

        fetch_end = min(today, end_date)
        season_dates = [
            date_value for date_value in existing_dates
            if start_date <= date_value <= fetch_end
        ]
        latest_date = max(season_dates) if season_dates else None
        fetch_start = start_date if latest_date is None else latest_date + timedelta(days=1)

        if fetch_start > fetch_end:
            print("No new dates to fetch. Latest date:", latest_date)
            return

        for date_pointer in iter_dates(fetch_start, fetch_end):
            print("Getting data:", date_pointer)
            # 1. Fetch Season Data
            df = fetch_data(url, date_pointer, value["start_year"], season_key)
            if not df.empty:
                table_name = date_pointer.strftime("%Y-%m-%d")
                df["Date"] = table_name
                df.to_sql(table_name, con, if_exists="replace", index=False)
            else:
                print("No data returned for:", date_pointer)

            # 2. Fetch Last 10 Games Data
            df_ten = fetch_data(url_ten, date_pointer, value["start_year"], season_key)
            if not df_ten.empty:
                table_name_ten = date_pointer.strftime("%Y-%m-%d") + "_L10"
                df_ten["Date"] = table_name_ten
                df_ten.to_sql(table_name_ten, con, if_exists="replace", index=False)
            else:
                print("No L10 data returned for:", date_pointer)

            # 3. Fetch Advanced Season Data (OFF_RATING, DEF_RATING, NET_RATING)
            df_adv = fetch_data(url_adv, date_pointer, value["start_year"], season_key)
            if not df_adv.empty:
                table_name_adv = date_pointer.strftime("%Y-%m-%d") + "_ADV"
                df_adv["Date"] = table_name_adv
                df_adv.to_sql(table_name_adv, con, if_exists="replace", index=False)
            else:
                print("No ADV data returned for:", date_pointer)

            # 4. Fetch Advanced Last 10 Games Data
            df_adv_ten = fetch_data(url_adv_ten, date_pointer, value["start_year"], season_key)
            if not df_adv_ten.empty:
                table_name_adv_ten = date_pointer.strftime("%Y-%m-%d") + "_ADV_L10"
                df_adv_ten["Date"] = table_name_adv_ten
                df_adv_ten.to_sql(table_name_adv_ten, con, if_exists="replace", index=False)
            else:
                print("No ADV_L10 data returned for:", date_pointer)

            time.sleep(random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

            # TODO: Add tests


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch NBA team stats data.")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Fetch all missing dates for seasons in config.toml.",
    )
    parser.add_argument(
        "--season",
        help="Limit backfill to a single season key (e.g. 2025-26).",
    )
    args = parser.parse_args()
    main(backfill=args.backfill, season=args.season)
