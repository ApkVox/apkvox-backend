"""
NotiaBet API - FastAPI Backend

Exposes NBA predictions via REST API for mobile app consumption.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
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
    try:
        init_db()
        print("[API] Database ready")
    except Exception as e:
        print(f"[API] WARNING: Database initialization failed: {e}")
        print("[API] Server will continue without database - some features may be unavailable")
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


class AIImpact(BaseModel):
    summary: str
    impact_score: float
    key_factors: List[str]
    confidence: float


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
    recommendation: Optional[str] = "SKIP"
    edge_percent: Optional[float] = 0.0
    ai_impact: Optional[AIImpact] = None
    status: Optional[str] = "SCHEDULED"
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    actual_winner: Optional[str] = None
    is_correct: Optional[int] = None


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
    ai_impact: Optional[Any] = None # For history, might be stored as JSON
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
async def get_predictions(
    sportsbook: str = Query("fanduel", description="Sportsbook to fetch odds from"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format to fetch past/future games"),
    days: int = Query(1, description="Number of days to fetch (1-3, default 1 for speed)", ge=1, le=3)
):
    """
    Get predictions for a specific date. If no date is provided, defaults to today.
    Use 'days' parameter to fetch 1-3 days of predictions (default: 1 for fast response).
    """
    try:
        service = get_prediction_service(sportsbook=sportsbook)
        
        target_predictions = []
        
        if date:
            try:
                # Parse date string
                target_dt = datetime.strptime(date, "%Y-%m-%d")
                target_date = target_dt.date()
                today = get_current_date() # From timezone module
                
                # Check if date is in the past
                if target_date < today:
                    from .database import get_history
                    from .audit import audit_predictions
                    
                    # 1. Check if we have predictions in DB
                    existing = get_history(limit=1, game_date=date)
                    
                    if not existing:
                        # AUTO-BACKFILL: Generate predictions retroactively
                        print(f"[API] No predictions found for past date {date}. Generating retroactive predictions...")
                        # This generates AND SAVES to DB
                        service.get_upcoming_predictions(target_date=target_dt)
                    
                    # 2. Trigger Audit (Updates scores/winners)
                    audit_stats = audit_predictions(target_dt)
                    print(f"[API] Audit Triggered for {date}: {audit_stats}")
                    
                    # 3. Fetch Final Result
                    history_records = get_history(limit=100, game_date=date)
                    
                    # Convert HistoryRecord dicts to PredictionResponse objects
                    for rec in history_records:
                        # Map field names from DB schema to API schema
                        rec["timestamp"] = rec.get("created_at", "") or ""
                        rec["start_time_utc"] = (rec.get("game_date") or "") + "T00:00:00Z"
                        rec["winner_confidence"] = rec.get("confidence", 0) or 0
                        rec["home_win_probability"] = rec.get("home_win_probability", 0) or 0
                        rec["away_win_probability"] = rec.get("away_win_probability", 0) or 0
                        rec["ou_confidence"] = rec.get("ou_confidence", 0) or 0
                        rec["under_over_line"] = rec.get("under_over_line", 0) or 0
                        rec["under_over_prediction"] = rec.get("under_over_prediction", "N/A") or "N/A"
                        target_predictions.append(rec)
                        
                else:
                    # Future/Today: Use Predictor Service
                    # Now supports target_date!
                    target_predictions = service.get_upcoming_predictions(target_date=target_dt)
                    
            except ValueError:
                 return JSONResponse(
                    status_code=400,
                    content={"message": "Invalid date format. Use YYYY-MM-DD"}
                )
        else:
            # Default: Use the 'days' parameter (default: 1 for speed)
            target_predictions = service.get_upcoming_predictions(days=days)

        return PredictionsListResponse(
            count=len(target_predictions),
            predictions=[PredictionResponse(**p) for p in target_predictions],
            generated_at=get_current_timestamp()
        )
    except Exception as e:
        # Return empty list on error instead of failing
        import traceback
        print(f"[API] Error getting predictions: {e}")
        traceback.print_exc()
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


# ============================================================
# AI Analysis Endpoints (On-Demand)
# ============================================================

class AnalyzeResponse(BaseModel):
    status: str
    team: str
    message: str


@app.post("/api/analyze/{team_name}", response_model=AnalyzeResponse, tags=["AI Analysis"])
async def analyze_team(team_name: str, background_tasks: BackgroundTasks):
    """
    Trigger AI analysis for a specific team.
    Analysis runs in background - results cached in database.
    Call /api/predictions after a few seconds to see updated ai_impact.
    """
    from .ai_worker import run_single_analysis
    
    # Run analysis in background (non-blocking)
    background_tasks.add_task(run_single_analysis, team_name)
    
    return AnalyzeResponse(
        status="analyzing",
        team=team_name,
        message=f"Analysis started for {team_name}. Check predictions in ~5 seconds."
    )


@app.post("/api/analyze/all", tags=["AI Analysis"])
async def analyze_all_teams(background_tasks: BackgroundTasks):
    """
    Trigger AI analysis for all teams playing today.
    This is the same as running: python -m backend.ai_worker
    """
    from .ai_worker import run_daily_analysis
    
    background_tasks.add_task(run_daily_analysis)
    
    return {
        "status": "analyzing",
        "message": "Daily analysis started for all teams. Check predictions in ~30-60 seconds."
    }
