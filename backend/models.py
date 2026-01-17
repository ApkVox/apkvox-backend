from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class AIImpact(BaseModel):
    summary: str = Field(default="Sin análisis")
    impact_score: float = Field(default=0.0)
    key_factors: List[str] = Field(default_factory=list)
    confidence: int = Field(default=0)

class PredictionGame(BaseModel):
    home_team: str
    away_team: str
    start_time_utc: str
    status: str = Field(default="SCHEDULED")
    
    # Prediction details
    predicted_winner: str = Field(default="N/A")
    winner_confidence: float = Field(default=0.0)
    home_win_probability: float = Field(default=50.0)
    away_win_probability: float = Field(default=50.0)
    
    # Odds
    home_odds: float = Field(default=0.0)
    away_odds: float = Field(default=0.0)
    
    # Over/Under
    under_over_prediction: str = Field(default="N/A")
    under_over_line: float = Field(default=0.0)
    ou_confidence: float = Field(default=0.0)
    
    # Results
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)
    actual_winner: str = Field(default="N/A")
    is_correct: Optional[int] = Field(default=None)
    
    # Metadata
    recommendation: str = Field(default="NO DATA")
    edge_percent: float = Field(default=0.0)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # AI Analysis
    ai_impact: AIImpact = Field(default_factory=AIImpact)

class DailyPredictionsPayload(BaseModel):
    meta: Dict[str, Any]
    games: List[PredictionGame]
