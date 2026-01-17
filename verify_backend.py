
import requests
import time
import sys
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def check_health():
    url = f"{BASE_URL}/health"
    try:
        log(f"Checking {url}...")
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            log(f"Health Check Passed: {data}", "SUCCESS")
            return True
        else:
            log(f"Health Check Failed: {response.status_code} - {response.text}", "ERROR")
            return False
    except Exception as e:
        log(f"Health Check Connection Error: {e}", "ERROR")
        return False

def check_predictions():
    # Test for today
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"{BASE_URL}/api/predictions?date={today}"
    try:
        log(f"Checking {url}...")
        response = requests.get(url, timeout=30) # Predictions can take time if scraping
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            log(f"Predictions Check Passed. Found {count} predictions for {today}.", "SUCCESS")
            if count > 0:
                log(f"Sample prediction: {json.dumps(data['predictions'][0], indent=2)}")
            return True
        else:
            log(f"Predictions Check Failed: {response.status_code} - {response.text}", "ERROR")
            return False
    except Exception as e:
        log(f"Predictions Check Connection Error: {e}", "ERROR")
        return False

def check_history():
    url = f"{BASE_URL}/api/history?limit=5"
    try:
        log(f"Checking {url}...")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            count = data.get("count", 0)
            log(f"History Check Passed. Found {count} records.", "SUCCESS")
            return True
        else:
            log(f"History Check Failed: {response.status_code} - {response.text}", "ERROR")
            return False
    except Exception as e:
        log(f"History Check Connection Error: {e}", "ERROR")
        return False

def check_stats():
    url = f"{BASE_URL}/api/stats"
    try:
        log(f"Checking {url}...")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            log(f"Stats Check Passed: {data}", "SUCCESS")
            return True
        else:
            log(f"Stats Check Failed: {response.status_code} - {response.text}", "ERROR")
            return False
    except Exception as e:
        log(f"Stats Check Connection Error: {e}", "ERROR")
        return False

def main():
    log("Starting Backend Verification...", "START")
    
    # Wait for server to be up
    retries = 5
    server_up = False
    while retries > 0:
        if check_health():
            server_up = True
            break
        retries -= 1
        log(f"Waiting for server... ({retries} retries left)")
        time.sleep(2)
        
    if not server_up:
        log("Server is not reachable. Is it running?", "FATAL")
        sys.exit(1)
        
    # Run other checks
    results = [
        check_predictions(),
        check_history(),
        check_stats()
    ]
    
    if all(results):
        log("All checks passed!", "SUCCESS")
        sys.exit(0)
    else:
        log("Some checks failed.", "WARNING")
        sys.exit(1)

if __name__ == "__main__":
    main()
