import requests
import json
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

# Original URL template
# {2} -> Start Year (e.g. 2025)
# {0} -> Month
# {1} -> Day
# {3} -> Year
# {4} -> Season (e.g. 2025-26)

# Test Date: Jan 10, 2026
# Params: 0=1, 1=10, 2=2025, 3=2026, 4=2025-26
u_orig = "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=10%2F01%2F2025&DateTo=01%2F10%2F2026&Division=&GameScope=&GameSegment=&LastNGames=10&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2025-26&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="

# Variant: No DateFrom
u_no_from = "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateTo=01%2F10%2F2026&Division=&GameScope=&GameSegment=&LastNGames=10&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2025-26&SeasonSegment=&SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&TwoWay=0&VsConference=&VsDivision="

def test_url(name, url):
    print(f"Testing {name}...")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            row_count = len(data['resultSets'][0]['rowSet'])
            print(f"Rows returned: {row_count}")
        else:
            print("Error response")
    except Exception as e:
        print(f"Exception: {e}")

test_url("Original", u_orig)
time.sleep(1)
test_url("No DateFrom", u_no_from)
