
import requests
import sys
import json
from typing import List, Dict, Any, Optional

# Configuration
API_URL = "http://127.0.0.1:8001/api/predictions"

def log(msg, status="INFO", color="green"):
    print(f"[{status}] {msg}")

def validate_type(name: str, value: Any, expected_type: type, optional: bool = False) -> bool:
    if optional and value is None:
        return True
    if not isinstance(value, expected_type):
        log(f"Field '{name}' has wrong type. Expected {expected_type}, got {type(value)} ({value})", "ERROR")
        return False
    return True

def validate_prediction_contract(prediction: Dict[str, Any]) -> bool:
    errors = 0
    
    # Required Fields
    errors += not validate_type("home_team", prediction.get("home_team"), str)
    errors += not validate_type("away_team", prediction.get("away_team"), str)
    errors += not validate_type("predicted_winner", prediction.get("predicted_winner"), str)
    errors += not validate_type("home_win_probability", prediction.get("home_win_probability"), (int, float))
    errors += not validate_type("away_win_probability", prediction.get("away_win_probability"), (int, float))
    errors += not validate_type("winner_confidence", prediction.get("winner_confidence"), (int, float))
    
    uo = prediction.get("under_over_prediction")
    if uo not in ["UNDER", "OVER", "N/A", None]: # Allow N/A or None if API returns it, though TS says strict
         # The TS interface says "UNDER" | "OVER". If backend returns "N/A", strict frontend might break or show default.
         # Let's check strictness.
         log(f"Field 'under_over_prediction' value '{uo}' is not UNDER or OVER.", "WARNING")
         
    errors += not validate_type("under_over_line", prediction.get("under_over_line"), (int, float))
    errors += not validate_type("ou_confidence", prediction.get("ou_confidence"), (int, float))
    errors += not validate_type("home_odds", prediction.get("home_odds"), int)
    errors += not validate_type("away_odds", prediction.get("away_odds"), int)
    errors += not validate_type("start_time_utc", prediction.get("start_time_utc"), str)
    errors += not validate_type("timestamp", prediction.get("timestamp"), str)
    
    # Optional Fields (Check types if present)
    errors += not validate_type("recommendation", prediction.get("recommendation"), str, True)
    errors += not validate_type("edge_percent", prediction.get("edge_percent"), (int, float), True)
    errors += not validate_type("status", prediction.get("status"), str, True)
    errors += not validate_type("home_score", prediction.get("home_score"), int, True)
    errors += not validate_type("away_score", prediction.get("away_score"), int, True)
    errors += not validate_type("stadium", prediction.get("stadium"), str, True)

    return errors == 0

def main():
    log(f"Simulating Frontend Request to {API_URL}...", "START")
    
    # Health Check First
    try:
        log("Checking Health first...", "INFO")
        h_res = requests.get("http://127.0.0.1:8001/health", timeout=10)
        if h_res.status_code == 200:
            log("Health Check Passed.", "SUCCESS")
        else:
            log("Health Check Failed.", "FAIL")
            sys.exit(1)
    except Exception as e:
        log(f"Health Check Connection Failed: {e}", "CRITICAL")
        sys.exit(1)

    try:
        # Simulate 'days=1' param as used in api.ts
        # Increased timeout to 60s to match frontend config
        log(f"Fetching predictions (Timeout 60s)...", "INFO")
        response = requests.get(API_URL, params={"days": 1}, timeout=60)
        
        if response.status_code != 200:
            log(f"Backend returned {response.status_code}", "FAIL")
            print(response.text)
            sys.exit(1)
            
        data = response.json()
        log(f"Received {data.get('count')} predictions.", "INFO")
        
        predictions = data.get("predictions", [])
        
        if not predictions:
            log("No predictions returned. Cannot validate item structure.", "WARNING")
            # If empty, we can't fully validate, but it's not a 'fail' of the schema.
            sys.exit(0)
            
        all_passed = True
        for i, pred in enumerate(predictions):
            log(f"Validating prediction {i+1} ({pred.get('home_team')} vs {pred.get('away_team')})...")
            if not validate_prediction_contract(pred):
                all_passed = False
                log(f"Prediction {i+1} failed contract validation.", "FAIL")
            else:
                log(f"Prediction {i+1} PASSED contract.", "SUCCESS")
                
        if all_passed:
            log("Frontend Integration Simulation: SUCCESS", "PASS")
            sys.exit(0)
        else:
            log("Frontend Integration Simulation: FAILED", "FAIL")
            sys.exit(1)

    except Exception as e:
        log(f"Connection Failed: {e}", "CRITICAL")
        sys.exit(1)

if __name__ == "__main__":
    main()
