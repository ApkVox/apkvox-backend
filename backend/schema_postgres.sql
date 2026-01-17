-- 1. Create the predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    prediction_date DATE NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Insert mock data for verification
-- Using valid JSONB format for the payload
INSERT INTO predictions (prediction_date, payload)
VALUES (
    CURRENT_DATE, -- Uses today's date
    '{
        "meta": {
            "model": "XGBoost_v1",
            "generated_at": "2026-01-16T23:00:00Z"
        },
        "games": [
            {
                "home_team": "Los Angeles Lakers",
                "away_team": "Golden State Warriors",
                "predicted_winner": "Los Angeles Lakers",
                "home_win_probability": 0.585,
                "away_win_probability": 0.415,
                "confidence": 58.5,
                "status": "SCHEDULED"
            },
            {
                "home_team": "Boston Celtics",
                "away_team": "Miami Heat",
                "predicted_winner": "Boston Celtics",
                "home_win_probability": 0.72,
                "away_win_probability": 0.28,
                "confidence": 72.0,
                "status": "FINAL"
            }
        ]
    }'::jsonb
);

-- 3. Verify the data
SELECT * FROM predictions;
