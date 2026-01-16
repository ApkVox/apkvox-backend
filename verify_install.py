import sys
import os
from pathlib import Path

# Add root to sys.path
sys.path.insert(0, os.getcwd())

try:
    from backend.predictor import get_prediction_service
    
    print("Initializing Prediction Service...")
    service = get_prediction_service()
    
    print("Loading Models...")
    if not service.load_models():
        print("Failed to load models!")
        sys.exit(1)
        
    print("Fetching Predictions for next 3 days...")
    predictions = service.get_todays_predictions()
    
    print(f"Success! Generated {len(predictions)} predictions.")
    for p in predictions[:2]:
        print(f"Sample: {p['home_team']} vs {p['away_team']} -> {p['predicted_winner']} ({p['winner_confidence']}%)")
        
except Exception as e:
    print(f"Verification Failed: {e}")
    import traceback
    traceback.print_exc()
