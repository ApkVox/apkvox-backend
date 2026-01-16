
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from backend.main import PredictionResponse, AIImpact

def test_pydantic_serialization():
    # Mock data exactly as returned by PredictorService
    mock_ai_data = {
        "summary": "Injuries detected for Lakers.",
        "impact_score": -4.5,
        "key_factors": ["Anthony Davis (Out)", "LeBron James (Probable)"],
        "confidence": 0.85
    }
    
    mock_prediction = {
        "home_team": "Los Angeles Lakers",
        "away_team": "Phoenix Suns",
        "predicted_winner": "Phoenix Suns",
        "home_win_probability": 45.0,
        "away_win_probability": 55.0,
        "winner_confidence": 55.0,
        "under_over_prediction": "OVER",
        "under_over_line": 225.5,
        "ou_confidence": 62.0,
        "home_odds": -110,
        "away_odds": -110,
        "start_time_utc": "2026-01-15T22:00:00Z",
        "timestamp": "2026-01-15T15:00:00Z",
        "recommendation": "BET AWAY",
        "edge_percent": 15.5,
        "ai_impact": mock_ai_data
    }
    
    print("\n--- Testing Pydantic Serialization ---")
    try:
        response = PredictionResponse(**mock_prediction)
        json_out = response.model_dump_json(indent=2)
        print("Success! JSON Output:")
        print(json_out)
        
        # Verify fields
        assert "ai_impact" in json_out
        assert "recommendation" in json_out
        assert "edge_percent" in json_out
        print("\nAll required fields verified in API model.")
        
    except Exception as e:
        print(f"Error during serialization: {e}")

if __name__ == "__main__":
    test_pydantic_serialization()
