import sys
import os
import pandas as pd

# Add root to sys.path
sys.path.insert(0, os.getcwd())

from backend.predictor import get_prediction_service, SCHEDULE_PATH

print(f"Loading schedule from: {SCHEDULE_PATH}")
df = pd.read_csv(SCHEDULE_PATH)
print("Columns found:")
for col in df.columns:
    print(f" - {col}")
