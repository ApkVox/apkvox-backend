"""
Database Layer for NotiaBet

Handles SQLite persistence for predictions history and win rate tracking.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Timezone-aware date handling
from .timezone import get_current_timestamp

# Database path - in backend folder
DB_PATH = Path(__file__).parent / "app.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection with row factory for dict results"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initialize database with predictions table.
    Creates table if not exists with unique constraint to prevent duplicates.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            predicted_winner TEXT NOT NULL,
            home_win_probability REAL,
            away_win_probability REAL,
            confidence REAL NOT NULL,
            under_over_prediction TEXT,
            under_over_line REAL,
            ou_confidence REAL,
            home_odds INTEGER DEFAULT 0,
            away_odds INTEGER DEFAULT 0,
            result TEXT DEFAULT NULL,
            actual_winner TEXT DEFAULT NULL,
            is_correct INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'SCHEDULED',
            home_score INTEGER DEFAULT NULL,
            away_score INTEGER DEFAULT NULL,
            UNIQUE(game_date, home_team, away_team)
        )
    """)
    
    # Create index for faster queries by date
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_date 
        ON predictions(game_date DESC)
    """)
    
    # Migration: Check if new columns exist, if not add them
    try:
        cursor.execute("SELECT status, home_score, away_score FROM predictions LIMIT 1")
    except sqlite3.OperationalError:
        print("[Database] Migrating schema: adding scores and status columns...")
        try:
            cursor.execute("ALTER TABLE predictions ADD COLUMN status TEXT DEFAULT 'SCHEDULED'")
        except: pass
        try:
            cursor.execute("ALTER TABLE predictions ADD COLUMN home_score INTEGER DEFAULT NULL")
        except: pass
        try:
            cursor.execute("ALTER TABLE predictions ADD COLUMN away_score INTEGER DEFAULT NULL")
        except: pass
    
    # AI Insights cache table for background-processed AI analysis
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            game_date TEXT NOT NULL,
            summary TEXT,
            impact_score REAL DEFAULT 0.0,
            key_factors TEXT,
            confidence INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            UNIQUE(team_name, game_date)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_insights_team_date 
        ON ai_insights(team_name, game_date)
    """)
    
    conn.commit()
    conn.close()
    print("[Database] Initialized predictions and ai_insights tables")


def save_predictions(predictions: List[Dict[str, Any]]) -> int:
    """
    Save predictions to database using INSERT OR IGNORE.
    Returns number of new predictions saved (ignores duplicates).
    """
    if not predictions:
        return 0
    
    conn = get_connection()
    cursor = conn.cursor()
    
    saved_count = 0
    for pred in predictions:
        try:
            # Extract game date from start_time_utc (actual game date) or fall back to timestamp
            start_time = pred.get("start_time_utc")
            timestamp = pred.get("timestamp", get_current_timestamp())
            
            if start_time:
                # Use game's actual start time for date, adjusted for NBA timezone
                # (UTC 05:00 next day is still "today" in NBA/EST)
                # Subtract 6 hours from UTC to safe-guard "late night" games belonging to previous day
                try:
                    # Robust parsing for "2026-01-14T00:30:00Z" or similar
                    clean_time = start_time.replace('T', ' ').replace('Z', '')
                    dt = datetime.strptime(clean_time, "%Y-%m-%d %H:%M:%S")
                    nba_date = (dt - timedelta(hours=6)).date()
                    game_date = str(nba_date)
                except Exception:
                    # Fallback if parsing fails
                    game_date = start_time.split("T")[0]
            else:
                # Fallback to timestamp if no start_time
                game_date = timestamp.split("T")[0]
            
            cursor.execute("""
                INSERT OR IGNORE INTO predictions (
                    game_date, home_team, away_team, predicted_winner,
                    home_win_probability, away_win_probability, confidence,
                    under_over_prediction, under_over_line, ou_confidence,
                    home_odds, away_odds, created_at,
                    status, home_score, away_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_date,
                pred.get("home_team"),
                pred.get("away_team"),
                pred.get("predicted_winner"),
                pred.get("home_win_probability"),
                pred.get("away_win_probability"),
                pred.get("winner_confidence"),
                pred.get("under_over_prediction"),
                pred.get("under_over_line"),
                pred.get("ou_confidence"),
                pred.get("home_odds", 0),
                pred.get("away_odds", 0),
                timestamp,
                pred.get("status", "SCHEDULED"),
                pred.get("home_score"),
                pred.get("away_score")
            ))
            
            if cursor.rowcount > 0:
                saved_count += 1
                
        except Exception as e:
            print(f"[Database] Error saving prediction: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    if saved_count > 0:
        print(f"[Database] Saved {saved_count} new predictions")
    
    return saved_count


def get_history(limit: int = 100, game_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get prediction history from database.
    
    Args:
        limit: Maximum number of records to return
        game_date: Optional filter by specific date (YYYY-MM-DD)
    
    Returns:
        List of prediction records as dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if game_date:
        cursor.execute("""
            SELECT * FROM predictions 
            WHERE game_date = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (game_date, limit))
    else:
        cursor.execute("""
            SELECT * FROM predictions 
            ORDER BY game_date DESC, created_at DESC
            LIMIT ?
        """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convert Row objects to dicts
    return [dict(row) for row in rows]


def update_prediction_result(game_date: str, home_team: str, away_team: str, 
                             home_score: int, away_score: int, status: str) -> bool:
    """
    Manually update prediction result (for debugging or scraper updates).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Determine actual winner
        actual_winner = home_team if home_score > away_score else away_team
        
        # Check prediction
        cursor.execute("""
            SELECT predicted_winner FROM predictions
            WHERE game_date = ? AND home_team = ? AND away_team = ?
        """, (game_date, home_team, away_team))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        predicted = row["predicted_winner"]
        is_correct = 1 if predicted == actual_winner else 0
        
        cursor.execute("""
            UPDATE predictions
            SET status = ?, home_score = ?, away_score = ?, 
                actual_winner = ?, is_correct = ?
            WHERE game_date = ? AND home_team = ? AND away_team = ?
        """, (status, home_score, away_score, actual_winner, is_correct, 
              game_date, home_team, away_team))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"[Database] Error updating manual result: {e}")
        conn.close()
        return False


def get_stats() -> Dict[str, Any]:
    """
    Get prediction statistics (win rate, total predictions, etc.)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total predictions
    cursor.execute("SELECT COUNT(*) as total FROM predictions")
    total = cursor.fetchone()["total"]
    
    # Completed predictions (with results)
    cursor.execute("SELECT COUNT(*) as completed FROM predictions WHERE result = 'completed'")
    completed = cursor.fetchone()["completed"]
    
    # Correct predictions
    cursor.execute("SELECT COUNT(*) as correct FROM predictions WHERE is_correct = 1")
    correct = cursor.fetchone()["correct"]
    
    # Win rate
    win_rate = (correct / completed * 100) if completed > 0 else 0
    
    conn.close()
    
    return {
        "total_predictions": total,
        "completed_games": completed,
        "correct_predictions": correct,
        "win_rate": round(win_rate, 2),
        "pending_games": total - completed
    }


# ============================================================
# AI Insights Cache Functions
# ============================================================

def save_ai_insight(team_name: str, game_date: str, insight: Dict[str, Any]) -> bool:
    """
    Save AI analysis result to cache with 6-hour expiration.
    Uses INSERT OR REPLACE to update existing entries.
    """
    import json
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        now = datetime.now()
        expires = now + timedelta(hours=6)
        
        # Convert key_factors list to JSON string
        key_factors_json = json.dumps(insight.get("key_factors", []))
        
        cursor.execute("""
            INSERT OR REPLACE INTO ai_insights (
                team_name, game_date, summary, impact_score, 
                key_factors, confidence, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_name,
            game_date,
            insight.get("summary", ""),
            insight.get("impact_score", 0.0),
            key_factors_json,
            insight.get("confidence", 0),
            now.isoformat(),
            expires.isoformat()
        ))
        
        conn.commit()
        conn.close()
        print(f"[Database] Saved AI insight for {team_name} on {game_date}")
        return True
        
    except Exception as e:
        print(f"[Database] Error saving AI insight: {e}")
        conn.close()
        return False


def get_ai_insight(team_name: str, game_date: str) -> Optional[Dict[str, Any]]:
    """
    Get cached AI insight for a team on a specific date.
    Returns None if not found or expired.
    """
    import json
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT summary, impact_score, key_factors, confidence, expires_at
            FROM ai_insights
            WHERE team_name = ? AND game_date = ?
        """, (team_name, game_date))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Check expiration
        expires_at = datetime.fromisoformat(row["expires_at"])
        if datetime.now() > expires_at:
            return None  # Expired
        
        # Parse key_factors from JSON
        key_factors = json.loads(row["key_factors"]) if row["key_factors"] else []
        
        return {
            "summary": row["summary"],
            "impact_score": row["impact_score"],
            "key_factors": key_factors,
            "confidence": row["confidence"]
        }
        
    except Exception as e:
        print(f"[Database] Error getting AI insight: {e}")
        conn.close()
        return None


def get_insights_for_date(game_date: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all cached AI insights for a specific game date.
    Returns dict keyed by team_name.
    """
    import json
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT team_name, summary, impact_score, key_factors, confidence, expires_at
            FROM ai_insights
            WHERE game_date = ?
        """, (game_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        now = datetime.now()
        insights = {}
        
        for row in rows:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if now <= expires_at:  # Not expired
                key_factors = json.loads(row["key_factors"]) if row["key_factors"] else []
                insights[row["team_name"]] = {
                    "summary": row["summary"],
                    "impact_score": row["impact_score"],
                    "key_factors": key_factors,
                    "confidence": row["confidence"]
                }
        
        return insights
        
    except Exception as e:
        print(f"[Database] Error getting insights for date: {e}")
        conn.close()
        return {}
