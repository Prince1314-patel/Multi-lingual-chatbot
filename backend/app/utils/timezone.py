"""
Timezone Utilities

This module provides timezone-aware datetime utilities for the application.
It replaces deprecated datetime.utcnow() with IST timezone-aware datetime objects.

The module provides functions to get current time in IST timezone and
convert between different timezone formats.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


# IST timezone (UTC+5:30)
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


def get_current_time() -> datetime:
    """
    Get current time in IST timezone.
    
    This function replaces datetime.utcnow() with a timezone-aware
    datetime object in IST timezone.
    
    Returns:
        datetime: Current time in IST timezone
    """
    return datetime.now(IST_TIMEZONE)


def get_current_time_iso() -> str:
    """
    Get current time in IST timezone as ISO string.
    
    Returns:
        str: Current time in IST timezone as ISO format string
    """
    return get_current_time().isoformat()


def convert_to_ist(dt: datetime) -> datetime:
    """
    Convert a datetime object to IST timezone.
    
    If the datetime is naive (no timezone), it's assumed to be in UTC.
    If it has a timezone, it's converted to IST.
    
    Args:
        dt: datetime object to convert
        
    Returns:
        datetime: datetime object in IST timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(IST_TIMEZONE)


def convert_from_ist(dt: datetime) -> datetime:
    """
    Convert a datetime object from IST timezone to UTC.
    
    Args:
        dt: datetime object in IST timezone
        
    Returns:
        datetime: datetime object in UTC
    """
    if dt.tzinfo is None:
        # Assume IST if no timezone info
        dt = dt.replace(tzinfo=IST_TIMEZONE)
    
    return dt.astimezone(timezone.utc)


def parse_iso_to_ist(iso_string: str) -> datetime:
    """
    Parse ISO string to IST timezone datetime.
    
    Args:
        iso_string: ISO format datetime string
        
    Returns:
        datetime: datetime object in IST timezone
    """
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return convert_to_ist(dt)


def format_ist_time(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime in IST timezone.
    
    Args:
        dt: datetime object
        format_str: format string for datetime
        
    Returns:
        str: formatted datetime string in IST
    """
    ist_dt = convert_to_ist(dt)
    return ist_dt.strftime(format_str)


def get_time_difference_seconds(dt1: datetime, dt2: datetime) -> float:
    """
    Get time difference between two datetime objects in seconds.
    
    Args:
        dt1: first datetime object
        dt2: second datetime object
        
    Returns:
        float: time difference in seconds
    """
    # Convert both to IST for consistent comparison
    ist_dt1 = convert_to_ist(dt1)
    ist_dt2 = convert_to_ist(dt2)
    
    return (ist_dt2 - ist_dt1).total_seconds()


def is_time_expired(dt: datetime, expiry_minutes: int) -> bool:
    """
    Check if a datetime has expired based on current IST time.
    
    Args:
        dt: datetime to check
        expiry_minutes: minutes after which the datetime expires
        
    Returns:
        bool: True if expired, False otherwise
    """
    current_time = get_current_time()
    expiry_time = convert_to_ist(dt) + timedelta(minutes=expiry_minutes)
    
    return current_time > expiry_time
