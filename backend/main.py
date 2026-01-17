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
    background_tasks: BackgroundTasks,
    sportsbook: str = Query("fanduel", description="Sportsbook to fetch odds from"),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format to fetch past/future games"),
    days: int = Query(1, description="Number of days to fetch (1-3, default 1 for speed)", ge=1, le=3)
):
    """
    Get predictions for a specific date. If no date is provided, defaults to today.
    Use 'days' parameter to fetch 1-3 days of predictions (default: 1 for fast response).
    
    AUTO-TRIGGER: If AI insights are missing ("Análisis pendiente" or "Sin datos"),
    this endpoint queues a background analysis task for those teams.
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
                    from .scores import fetch_scores_for_date
                    
                    # 1. Check if we have predictions in DB
                    existing = get_history(limit=100, game_date=date)
                    
                    if existing:
                        # We have stored predictions - use them
                        history_records = existing
                        
                        # Trigger Audit to update scores
                        try:
                            audit_stats = audit_predictions(target_dt)
                            print(f"[API] Audit Triggered for {date}: {audit_stats}")
                            # Re-fetch after audit to get updated scores
                            history_records = get_history(limit=100, game_date=date)
                        except Exception as audit_err:
                            print(f"[API] Audit warning: {audit_err}")
                        
                        # Convert to API format
                        for rec in history_records:
                            rec["timestamp"] = rec.get("created_at", "") or ""
                            rec["start_time_utc"] = (rec.get("game_date") or "") + "T00:00:00Z"
                            rec["winner_confidence"] = rec.get("confidence", 0) or 0
                            rec["home_win_probability"] = rec.get("home_win_probability", 0) or 0
                            rec["away_win_probability"] = rec.get("away_win_probability", 0) or 0
                            rec["ou_confidence"] = rec.get("ou_confidence", 0) or 0
                            rec["under_over_line"] = rec.get("under_over_line", 0) or 0
                            rec["under_over_prediction"] = rec.get("under_over_prediction", "N/A") or "N/A"
                            rec["predicted_winner"] = rec.get("predicted_winner") or "N/A"
                            rec["home_odds"] = rec.get("home_odds") or 0
                            rec["away_odds"] = rec.get("away_odds") or 0
                            rec["status"] = rec.get("status", "FINAL")
                            rec["recommendation"] = rec.get("recommendation", "NO DATA")
                            # Ensure ai_impact is a dict if missing
                            if "ai_impact" not in rec or not rec["ai_impact"]:
                                rec["ai_impact"] = {
                                    "summary": "Sin análisis histórico",
                                    "impact_score": 0,
                                    "key_factors": [],
                                    "confidence": 0
                                }
                            target_predictions.append(rec)
                    else:
                        # No stored predictions - FALLBACK: Show schedule games with scores from CSV
                        print(f"[API] No predictions in DB for {date}. Showing schedule fallback...")
                        
                        # Get scores/games from CSV schedule
                        scores_data = fetch_scores_for_date(target_dt)
                        
                        if scores_data:
                            for key, game_data in scores_data.items():
                                # Key format is "HOME_ABBR:AWAY_ABBR"
                                # We need to convert abbreviations back to full names
                                from .audit import TEAM_MAP
                                
                                # Reverse lookup for team names
                                abbr_to_name = {v: k for k, v in TEAM_MAP.items() if len(k) > 5}
                                
                                home_abbr = game_data.get("home_abbr", "")
                                away_abbr = game_data.get("away_abbr", "")
                                
                                home_name = abbr_to_name.get(home_abbr, home_abbr)
                                away_name = abbr_to_name.get(away_abbr, away_abbr)
                                
                                home_score = game_data.get("home_score", 0)
                                away_score = game_data.get("away_score", 0)
                                actual_winner = home_name if home_score > away_score else away_name
                                
                                fallback_pred = {
                                    "home_team": home_name,
                                    "away_team": away_name,
                                    "predicted_winner": "N/A",  # No prediction available
                                    "home_win_probability": 50.0,
                                    "away_win_probability": 50.0,
                                    "winner_confidence": 0.0,
                                    "under_over_prediction": "N/A",
                                    "under_over_line": 0.0,
                                    "ou_confidence": 0.0,
                                    "home_odds": 0,
                                    "away_odds": 0,
                                    "start_time_utc": f"{date}T00:00:00Z",
                                    "timestamp": get_current_timestamp(),
                                    "recommendation": "NO DATA",
                                    "edge_percent": 0.0,
                                    "ai_impact": {
                                        "summary": "Sin predicción histórica disponible",
                                        "impact_score": 0.0,
                                        "key_factors": [],
                                        "confidence": 0
                                    },
                                    "status": "FINAL",
                                    "home_score": home_score,
                                    "away_score": away_score,
                                    "actual_winner": actual_winner,
                                    "is_correct": None  # Can't calculate without prediction
                                }
                                target_predictions.append(fallback_pred)
                        
                        print(f"[API] Fallback returned {len(target_predictions)} games from schedule")
                        
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

        # --- AUTO-TRIGGER AI ANALYSIS ---
        from .ai_worker import run_single_analysis
        
        teams_to_analyze = set()
        
        for p in target_predictions:
            # Check if AI data is missing or pending
            ai = p.get("ai_impact", {})
            summary = ai.get("summary", "") if ai else ""
            
            # Criteria for re-analysis:
            # 1. Summary contains "Análisis pendiente" (Pending)
            # 2. Summary contains "Sin datos" (No Data)
            # 3. Summary is empty
            if not summary or "pendiente" in summary.lower() or "sin datos" in summary.lower():
                home = p.get("home_team")
                away = p.get("away_team")
                if home: teams_to_analyze.add(home)
                if away: teams_to_analyze.add(away)
        
        if teams_to_analyze:
            print(f"[API] Triggering background AI analysis for {len(teams_to_analyze)} teams: {list(teams_to_analyze)}")
            for team in teams_to_analyze:
                background_tasks.add_task(run_single_analysis, team)

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
    from .predictor import reset_service
    
    def analyze_and_reset(team: str):
        """Run analysis and then reset service cache"""
        run_single_analysis(team)
        reset_service()  # Force predictions to regenerate with new AI insights
        print(f"[API] Analysis complete and cache reset for {team}")
    
    # Run analysis in background (non-blocking)
    background_tasks.add_task(analyze_and_reset, team_name)
    
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
    from .predictor import reset_service
    
    def analyze_all_and_reset():
        """Run daily analysis and then reset service cache"""
        run_daily_analysis()
        reset_service()  # Force predictions to regenerate with new AI insights
        print("[API] Daily analysis complete and cache reset")
    
    background_tasks.add_task(analyze_all_and_reset)
    
    return {
        "status": "analyzing",
        "message": "Daily analysis started for all teams. Check predictions in ~30-60 seconds."
    }

# =====================================================================
# FINTECH ENDPOINTS (The Automated Investment Manager)
# =====================================================================

from backend import finance_engine
from backend.sentinel_agent import sentinel

@app.get("/api/portfolio", tags=["Fintech"])
def get_portfolio():
    """Returns portfolio history and current stats."""
    history = database.get_portfolio_history(limit=30)
    return {"history": history}

class StrategyRequest(BaseModel):
    bankroll: float = 50000.0

@app.post("/api/strategy/optimize", tags=["Fintech"])
def optimize_strategy(request: StrategyRequest):
    """
    Takes current bankroll.
    Runs 'The Sniper Engine' on TODAY's predictions.
    Returns:
      - Proposed Bets (filtered by Edge > 15%, Odds > 1.60)
      - Kelly Stake Sizes
      - Sentinel Probable Risk Analysis (AI Text)
    """
    # 1. Get today's predictions
    today_str = get_current_date().strftime("%Y-%m-%d")
    raw_preds = get_history(limit=1, game_date=today_str) 
    
    if not raw_preds:
         try:
            raw_preds = get_prediction_service().get_predictions_for_date(today_str)
         except:
            raw_preds = []

    # 2. Optimize Portfolio (Kelly + Sniper)
    proposed_bets = finance_engine.optimize_portfolio(raw_preds, request.bankroll)
    
    # 3. Sentinel Risk Analysis
    # Convert bet models to dicts for AI
    bets_dicts = [bet.model_dump() for bet in proposed_bets]
    risk_advice = sentinel.analyze_risk(bets_dicts, request.bankroll)
    
    return {
        "strategy": "Sniper (Edge > 15%, Odds > 1.60)",
        "bankroll_used": request.bankroll,
        "proposed_bets": bets_dicts,
        "risk_analysis": {
            "advisor": "Sentinel AI",
            "message": risk_advice,
            "exposure_rating": "HIGH" if len(bets_dicts) > 5 else "MODERATE"
        }
    }
