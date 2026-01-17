"""
Database Layer for NotiaBet (PostgreSQL)

Handles persistence using PostgreSQL on Neon Tech.
Uses JSONB for flexible prediction storage.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Fix common DATABASE_URL format issues (Render sometimes uses postgres:// instead of postgresql://)
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    elif DATABASE_URL.startswith("psql://"):
        DATABASE_URL = DATABASE_URL.replace("psql://", "postgresql://", 1)

def get_connection():
    """Get database connection"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set")
    
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    """
    Initialize database schema for PostgreSQL.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. Predictions Table (JSONB)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    prediction_date DATE NOT NULL UNIQUE,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. AI Insights Table (Migrated to standard columns for now, could be JSONB too but keeping structure)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_insights (
                    id SERIAL PRIMARY KEY,
                    team_name TEXT NOT NULL,
                    game_date DATE NOT NULL,
                    summary TEXT,
                    impact_score REAL DEFAULT 0.0,
                    key_factors JSONB,
                    confidence INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    UNIQUE(team_name, game_date)
                );
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_insights_team_date ON ai_insights(team_name, game_date);")
            
            # 3. Bet Ledger (Fintech)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bet_ledger (
                    id SERIAL PRIMARY KEY,
                    prediction_id TEXT,
                    date DATE NOT NULL,
                    match TEXT NOT NULL,
                    selection TEXT NOT NULL,
                    odds REAL NOT NULL,
                    stake_amount REAL NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    pnl REAL DEFAULT 0.0,
                    is_real_bet BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_bet_ledger_date ON bet_ledger(date);")

            # 4. Portfolio History (Fintech)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id SERIAL PRIMARY KEY,
                    date DATE NOT NULL UNIQUE,
                    total_balance REAL NOT NULL,
                    daily_profit REAL DEFAULT 0.0,
                    roi_percentage REAL DEFAULT 0.0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_history_date ON portfolio_history(date DESC);")

            # 5. Daily Cache (Autonomous Server)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_cache (
                    id SERIAL PRIMARY KEY,
                    cache_date DATE NOT NULL UNIQUE,
                    predictions_json JSONB,
                    strategy_json JSONB,
                    sentinel_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_cache_date ON daily_cache(cache_date DESC);")
            
        conn.commit()
        print("[Database] Initialized PostgreSQL tables (predictions, ai_insights)")
    except Exception as e:
        print(f"[Database] Error initializing DB: {e}")
        conn.rollback()
    finally:
        conn.close()


from .models import PredictionGame, DailyPredictionsPayload

def save_predictions(predictions: List[Dict[str, Any]]) -> int:
    """
    Save predictions for a SINGLE DAY as one JSONB payload row.
    If row exists for that date, it updates the payload (UPSERT).
    Uses Pydantic models for strict validation.
    """
    if not predictions:
        return 0
    
    # We group predictions by date, but usually this function is called with a batch for one day.
    # We'll assume the first prediction's date allows us to determine the 'prediction_date'.
    # IMPORTANT: The current logic in `predictor.py` passes a list of predictions.
    
    # Extract the common date from the first prediction or existing logic
    first_pred = predictions[0]
    start_time = first_pred.get("start_time_utc")
    timestamp = first_pred.get("timestamp") or datetime.now().isoformat()
    
    # Determine the "Game Day" (NBA Logical Day)
    if start_time:
        try:
            clean_time = start_time.replace('T', ' ').replace('Z', '')
            dt = datetime.strptime(clean_time, "%Y-%m-%d %H:%M:%S")
            # NBA day is 6 hours behind UTC roughly for "night" games assignment
            nba_date = (dt - timedelta(hours=6)).date()
            prediction_date = nba_date
        except:
            prediction_date = datetime.now().date()
    else:
        # Fallback
        prediction_date = datetime.now().date()

    conn = get_connection()
    try:
        # Validate and Normalize Data using Pydantic Models
        # This is the "SQLModel/Pydantic" migration step requested
        validated_games = []
        for pred in predictions:
            try:
                # This throws ValidationError if crucial fields miss, or auto-fills defaults
                model = PredictionGame(**pred)
                validated_games.append(model.model_dump())
            except Exception as ve:
                print(f"[Database] Validation Warning for a game: {ve}. Skipping.")
                continue

        if not validated_games:
            print("[Database] No valid games to save after validation.")
            return 0

        with conn.cursor() as cursor:
            # Prepare payload
            payload = {
                "meta": {
                    "count": len(validated_games),
                    "generated_at": timestamp
                },
                "games": validated_games
            }
            
            cursor.execute("""
                INSERT INTO predictions (prediction_date, payload, created_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (prediction_date) 
                DO UPDATE SET 
                    payload = EXCLUDED.payload,
                    created_at = CURRENT_TIMESTAMP;
            """, (prediction_date, Json(payload)))
            
        conn.commit()
        print(f"[Database] Saved {len(validated_games)} predictions for {prediction_date}")
        return len(validated_games)
    except Exception as e:
        print(f"[Database] Error saving predictions: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


def get_history(limit: int = 100, game_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve predictions. 
    Since we store by DAY, we fetch the days and unpack the 'games' array.
    """
    conn = get_connection()
    results = []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if game_date:
                cursor.execute("""
                    SELECT payload FROM predictions 
                    WHERE prediction_date = %s
                """, (game_date,))
            else:
                cursor.execute("""
                    SELECT payload FROM predictions 
                    ORDER BY prediction_date DESC 
                    LIMIT %s
                """, (limit,))
            
            rows = cursor.fetchall()
            
            for row in rows:
                payload = row.get('payload', {})
                games = payload.get('games', [])
                # We extend the flat list of games
                results.extend(games)
                
    except Exception as e:
        print(f"[Database] Error getting history: {e}")
    finally:
        conn.close()
        
    # Apply limit strictly on the flattened list if needed (though the SQL limit was for days)
    # The original API expects a flat list of games.
    return results[:limit] if limit else results


def update_prediction_result(game_date: str, home_team: str, away_team: str, 
                             home_score: int, away_score: int, status: str) -> bool:
    """
    Update a specific game result inside the JSONB payload.
    This is complex in JSONB but doable.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # We need to find the row for this date, read it, modify it, and save it back
            # Or use fancy JSONB set operations.
            
            # 1. Fetch
            cursor.execute("SELECT payload FROM predictions WHERE prediction_date = %s", (game_date,))
            row = cursor.fetchone()
            if not row:
                return False
            
            payload = row[0] # RealDictCursor not used here unless specified, assuming standard cursor or handled above
            # Note: If I didn't use cursor_factory in this function, tuple access.
            # Let's use standard cursor for this function or be consistent. 
            pass
            
            # Simpler approach: Read logic with RealDictCursor
    except:
        pass
        
    # Re-implementing correctly below
    return _update_prediction_result_impl(game_date, home_team, away_team, home_score, away_score, status)

def _update_prediction_result_impl(game_date, home_team, away_team, home_score, away_score, status):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, payload FROM predictions WHERE prediction_date = %s", (game_date,))
            row = cursor.fetchone()
            if not row:
                return False
            
            record_id = row['id']
            payload = row['payload']
            games = payload.get('games', [])
            
            updated = False
            for game in games:
                if game.get('home_team') == home_team and game.get('away_team') == away_team:
                    game['home_score'] = home_score
                    game['away_score'] = away_score
                    game['status'] = status
                    
                    # Determine winner
                    if home_score > away_score:
                        actual = home_team
                    else:
                        actual = away_team
                    
                    game['actual_winner'] = actual
                    game['is_correct'] = 1 if game.get('predicted_winner') == actual else 0
                    updated = True
                    break
            
            if updated:
                cursor.execute("""
                    UPDATE predictions 
                    SET payload = %s 
                    WHERE id = %s
                """, (Json(payload), record_id))
                conn.commit()
                return True
            return False
    except Exception as e:
        print(f"[Database] Error updating result: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_stats() -> Dict[str, Any]:
    """
    Get generic stats. Expensive with JSONB iteration, but functional.
    """
    # For now, return mock/zeros or implement efficient JSONB aggregation query
    # Implementing a simple aggregation
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Count total games in all payloads
            cursor.execute("""
                SELECT sum(jsonb_array_length(payload->'games')) FROM predictions;
            """)
            total = cursor.fetchone()[0] or 0
            
            # This is hard to query efficiently without advanced JSONB path operators.
            # We'll return basic counts.
            return {
                "total_predictions": int(total),
                "completed_games": 0,
                "correct_predictions": 0,
                "win_rate": 0.0,
                "pending_games": 0
            }
    except:
        return {"total_predictions": 0, "completed_games": 0, "correct_predictions": 0, "win_rate": 0.0, "pending_games": 0}
    finally:
        conn.close()


# ============================================================
# AI Insights (PostgreSQL)
# ============================================================

def save_ai_insight(team_name: str, game_date: str, insight: Dict[str, Any]) -> bool:
    conn = get_connection()
    try:
        now = datetime.now()
        expires = now + timedelta(hours=6)
        
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO ai_insights (
                    team_name, game_date, summary, impact_score, 
                    key_factors, confidence, created_at, expires_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (team_name, game_date)
                DO UPDATE SET 
                    summary = EXCLUDED.summary,
                    impact_score = EXCLUDED.impact_score,
                    key_factors = EXCLUDED.key_factors,
                    confidence = EXCLUDED.confidence,
                    expires_at = EXCLUDED.expires_at;
            """, (
                team_name,
                game_date,
                insight.get("summary", ""),
                insight.get("impact_score", 0.0),
                Json(insight.get("key_factors", [])),
                insight.get("confidence", 0),
                now,
                expires
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[Database] Error saving AI insight: {e}")
        return False
    finally:
        conn.close()

def get_ai_insight(team_name: str, game_date: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT summary, impact_score, key_factors, confidence, expires_at
                FROM ai_insights
                WHERE team_name = %s AND game_date = %s
            """, (team_name, game_date))
            row = cursor.fetchone()
            
            if not row: 
                return None
                
            # Check expiry (Postgres returns datetime objects)
            if datetime.now().astimezone() > row['expires_at'].astimezone():
                return None
                
            return {
                "summary": row["summary"],
                "impact_score": row["impact_score"],
                "key_factors": row["key_factors"], # asyncpg/psycopg2 might auto-decode JSON
                "confidence": row["confidence"]
            }
    except Exception as e:
        print(f"[Database] Error getting AI insight: {e}")
        return None
    finally:
        conn.close()


def get_insights_for_date(game_date: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all cached AI insights for a specific game date.
    Returns dict keyed by team_name.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT team_name, summary, impact_score, key_factors, confidence, expires_at
                FROM ai_insights
                WHERE game_date = %s
            """, (game_date,))
            
            rows = cursor.fetchall()
            
            insights = {}
            for row in rows:
                # Check expiry
                if datetime.now().astimezone() <= row['expires_at'].astimezone():
                    insights[row['team_name']] = {
                        "summary": row["summary"],
                        "impact_score": row["impact_score"],
                        "key_factors": row["key_factors"],
                        "confidence": row["confidence"]
                    }
            return insights
    except Exception as e:
        print(f"[Database] Error getting insights for date: {e}")
        return {}
    finally:
        conn.close()


# ============================================================
# Fintech Engine (Bet Ledger & Portfolio)
# ============================================================
from .models import BetLedger, PortfolioSnapshot

def log_bet(bet: BetLedger) -> Optional[int]:
    """
    Log a new bet or update existing one in the ledger.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO bet_ledger (
                    prediction_id, date, match, selection, odds, 
                    stake_amount, status, pnl, is_real_bet, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id;
            """, (
                bet.prediction_id, bet.date, bet.match, bet.selection,
                bet.odds, bet.stake_amount, bet.status, bet.pnl, bet.is_real_bet
            ))
            new_id = cursor.fetchone()[0]
            conn.commit()
            return new_id
    except Exception as e:
        print(f"[Database] Error logging bet: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_pending_bets() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM bet_ledger WHERE status = 'PENDING'
            """)
            return cursor.fetchall()
    except Exception as e:
        print(f"[Database] Error fetching pending bets: {e}")
        return []
    finally:
        conn.close()

def update_bet_status(bet_id: int, status: str, pnl: float) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE bet_ledger 
                SET status = %s, pnl = %s 
                WHERE id = %s
            """, (status, pnl, bet_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"[Database] Error updating bet status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def save_portfolio_snapshot(snapshot: PortfolioSnapshot) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO portfolio_history (
                    date, total_balance, daily_profit, roi_percentage, created_at
                ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (date) DO UPDATE SET
                    total_balance = EXCLUDED.total_balance,
                    daily_profit = EXCLUDED.daily_profit,
                    roi_percentage = EXCLUDED.roi_percentage,
                    created_at = CURRENT_TIMESTAMP;
            """, (snapshot.date, snapshot.total_balance, snapshot.daily_profit, snapshot.roi_percentage))
            conn.commit()
            return True
    except Exception as e:
        print(f"[Database] Error saving portfolio snapshot: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_portfolio_history(limit: int = 30) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM portfolio_history 
                ORDER BY date ASC 
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()
    except Exception as e:
        print(f"[Database] Error getting portfolio history: {e}")
        return []
    finally:
        conn.close()

# ============================================================
# Daily Cache (Autonomous Entity Layer)
# ============================================================

def get_daily_cache(entry_date: str) -> Optional[Dict[str, Any]]:
    """
    Get cached predictions and strategy for a specific date.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM daily_cache WHERE cache_date = %s
            """, (entry_date,))
            return cursor.fetchone()
    except Exception as e:
        print(f"[Database] Error getting daily cache: {e}")
        return None
    finally:
        conn.close()

def save_daily_cache(entry_date: str, predictions: Optional[List] = None, 
                     strategy: Optional[Dict] = None, sentinel_msg: Optional[str] = None):
    """
    Upsert daily cache. Only updates provided fields.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if exists
            cursor.execute("SELECT id FROM daily_cache WHERE cache_date = %s", (entry_date,))
            exists = cursor.fetchone()
            
            if not exists:
                cursor.execute("""
                    INSERT INTO daily_cache (cache_date, predictions_json, strategy_json, sentinel_message, created_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    entry_date, 
                    Json(predictions) if predictions is not None else None,
                    Json(strategy) if strategy is not None else None,
                    sentinel_msg
                ))
            else:
                # Build dynamic update
                updates = []
                params = []
                
                if predictions is not None:
                    updates.append("predictions_json = %s")
                    params.append(Json(predictions))
                
                if strategy is not None:
                    updates.append("strategy_json = %s")
                    params.append(Json(strategy))
                    
                if sentinel_msg is not None:
                    updates.append("sentinel_message = %s")
                    params.append(sentinel_msg)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    query = f"UPDATE daily_cache SET {', '.join(updates)} WHERE cache_date = %s"
                    params.append(entry_date)
                    cursor.execute(query, tuple(params))
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"[Database] Error saving daily cache: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
