"""
Timezone Utilities for NotiaBet API

Centralizes all timezone-related logic to ensure consistent date handling
across the application, regardless of server location.
"""

from datetime import datetime, date
from zoneinfo import ZoneInfo

# Primary timezone for NBA games and user display
# America/New_York is the standard reference for NBA game schedules
NBA_TIMEZONE = ZoneInfo("America/New_York")

# Alternative: User timezone (Colombia)
USER_TIMEZONE = ZoneInfo("America/Bogota")


def get_current_datetime(tz: ZoneInfo = NBA_TIMEZONE) -> datetime:
    """
    Get current datetime in the specified timezone.
    
    Args:
        tz: Timezone to use (default: America/New_York for NBA)
        
    Returns:
        Timezone-aware datetime object
    """
    return datetime.now(tz)


def get_current_date(tz: ZoneInfo = NBA_TIMEZONE) -> date:
    """
    Get current date in the specified timezone.
    
    This is the CRITICAL function for determining "today's games".
    Uses NBA timezone (Eastern Time) by default since that's the
    reference timezone for NBA game schedules.
    
    Args:
        tz: Timezone to use (default: America/New_York for NBA)
        
    Returns:
        Date object representing "today" in the specified timezone
    """
    return datetime.now(tz).date()


def get_current_timestamp(tz: ZoneInfo = NBA_TIMEZONE) -> str:
    """
    Get current timestamp as ISO 8601 string with timezone info.
    
    Args:
        tz: Timezone to use (default: America/New_York for NBA)
        
    Returns:
        ISO 8601 formatted timestamp string
    """
    return datetime.now(tz).isoformat()


def is_same_day(game_date: date, tz: ZoneInfo = NBA_TIMEZONE) -> bool:
    """
    Check if a game date matches today in the specified timezone.
    
    Args:
        game_date: The date of the game
        tz: Timezone to use for "today" comparison
        
    Returns:
        True if game_date is "today" in the specified timezone
    """
    return game_date == get_current_date(tz)
