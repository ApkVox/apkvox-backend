"""
NotiaBet API - FastAPI Backend

Exposes NBA predictions via REST API for mobile app consumption.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

# Timezone-aware date handling
from .timezone import get_current_timestamp, get_current_date, NBA_TIMEZONE

from .predictor import get_prediction_service, NBAPredictionService
from .database import init_db, get_history, get_stats

# ============================================================
# Lifespan events (startup/shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[API] Initializing database...")
    init_db()
    print("[API] Database ready")
    yield
    # Shutdown
    print("[API] Shutting down...")

# ============================================================
# FastAPI Application Setup
# ============================================================
app = FastAPI(
    title="NotiaBet API",
    description="NBA Game Prediction API powered by XGBoost ML models",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ============================================================
# CORS Configuration (Required for React Native)
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for mobile app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Pydantic Models
# ============================================================
class HealthResponse(BaseModel):
    status: str
    model: str
    version: str
    timestamp: str


class PredictionResponse(BaseModel):
    home_team: str
    away_team: str
    predicted_winner: str
    home_win_probability: float
    away_win_probability: float
    winner_confidence: float
    under_over_prediction: str
    under_over_line: float
    ou_confidence: float
    home_odds: int
    away_odds: int
    start_time_utc: Optional[str]  # ISO 8601 format
    timestamp: str
    status: Optional[str] = "SCHEDULED"
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class PredictionsListResponse(BaseModel):
    count: int
    predictions: List[PredictionResponse]
    generated_at: str


class HistoryRecord(BaseModel):
    id: int
    game_date: str
    home_team: str
    away_team: str
    predicted_winner: str
    home_win_probability: Optional[float]
    away_win_probability: Optional[float]
    confidence: float
    under_over_prediction: Optional[str]
    under_over_line: Optional[float]
    ou_confidence: Optional[float]
    home_odds: int
    away_odds: int
    result: Optional[str]
    actual_winner: Optional[str]
    is_correct: Optional[int]
    created_at: str
    status: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class HistoryResponse(BaseModel):
    count: int
    records: List[HistoryRecord]
    generated_at: str


class StatsResponse(BaseModel):
    total_predictions: int
    completed_games: int
    correct_predictions: int
    win_rate: float
    pending_games: int


# ============================================================
# API Endpoints
# ============================================================
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns server status and model type.
    """
    return HealthResponse(
        status="ok",
        model="XGBoost",
        version="1.1.0",
        timestamp=get_current_timestamp()
    )


@app.get("/api/predictions", response_model=PredictionsListResponse, tags=["Predictions"])
async def get_predictions(sportsbook: Optional[str] = "fanduel"):
    """
    Get predictions for today's NBA games.

    Args:
        sportsbook: Sportsbook to fetch odds from (fanduel, draftkings, betmgm, etc.)

    Returns:
        List of predictions for today's games with win probabilities and O/U predictions.
        Returns empty list if no games today or data unavailable.
    """
    try:
        service = get_prediction_service(sportsbook=sportsbook)
        predictions = service.get_todays_predictions()

        return PredictionsListResponse(
            count=len(predictions),
            predictions=[PredictionResponse(**p) for p in predictions],
            generated_at=get_current_timestamp()
        )
    except Exception as e:
        # Return empty list on error instead of failing
        print(f"[API] Error getting predictions: {e}")
        return PredictionsListResponse(
            count=0,
            predictions=[],
            generated_at=get_current_timestamp()
        )


@app.get("/api/history", response_model=HistoryResponse, tags=["History"])
async def get_prediction_history(
    limit: int = 100,
    game_date: Optional[str] = None
):
    """
    Get prediction history from database.

    Args:
        limit: Maximum number of records to return (default 100)
        game_date: Optional filter by specific date (YYYY-MM-DD format)

    Returns:
        List of historical predictions with results if available.
    """
    try:
        records = get_history(limit=limit, game_date=game_date)
        return HistoryResponse(
            count=len(records),
            records=[HistoryRecord(**r) for r in records],
            generated_at=get_current_timestamp()
        )
    except Exception as e:
        print(f"[API] Error getting history: {e}")
        return HistoryResponse(
            count=0,
            records=[],
            generated_at=get_current_timestamp()
        )


@app.get("/api/stats", response_model=StatsResponse, tags=["History"])
async def get_prediction_stats():
    """
    Get prediction statistics including win rate.

    Returns:
        Stats including total predictions, completed games, correct predictions, and win rate.
    """
    try:
        stats = get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        print(f"[API] Error getting stats: {e}")
        return StatsResponse(
            total_predictions=0,
            completed_games=0,
            correct_predictions=0,
            win_rate=0.0,
            pending_games=0
        )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API info"""
    return {
        "name": "NotiaBet API",
        "version": "1.1.0",
        "model": "XGBoost",
        "endpoints": {
            "health": "/health",
            "predictions": "/api/predictions",
            "history": "/api/history",
            "stats": "/api/stats",
            "docs": "/docs"
        }
    }


# ============================================================
# Debug Endpoints (For testing UI states)
# ============================================================
class DebugResultRequest(BaseModel):
    game_date: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    status: str = "FINAL"

@app.post("/api/debug/set_result", tags=["Debug"])
async def set_debug_result(request: DebugResultRequest):
    """
    Manually set the result of a game to test UI states (Live/Final).
    """
    from .database import update_prediction_result
    
    success = update_prediction_result(
        request.game_date,
        request.home_team,
        request.away_team,
        request.home_score,
        request.away_score,
        request.status
    )
    
    if success:
        return {"status": "success", "message": "Game result updated"}
    else:
        raise HTTPException(status_code=404, detail="Prediction not found")
