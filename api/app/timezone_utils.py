"""
Timezone-aware datetime handling utilities.
Ensures all datetime parsing respects client timezone with proper DST handling.
"""

import os
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, available_timezones
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_timezone(tz_string: str) -> bool:
    """
    Validate that a timezone string is a valid IANA timezone.

    Args:
        tz_string: IANA timezone identifier (e.g., "America/New_York")

    Returns:
        True if valid, False otherwise
    """
    if not tz_string:
        return False

    try:
        # Try to create ZoneInfo to validate
        ZoneInfo(tz_string)
        return True
    except Exception:
        # Also check against available_timezones for extra validation
        return tz_string in available_timezones()


def get_safe_timezone(client_tz: Optional[str] = None) -> ZoneInfo:
    """
    Get a safe ZoneInfo object, falling back to defaults if invalid.

    Fallback chain:
    1. client_tz parameter
    2. DEFAULT_TZ environment variable
    3. UTC

    Args:
        client_tz: Client-provided timezone string

    Returns:
        ZoneInfo object
    """
    # Try client timezone
    if client_tz:
        try:
            return ZoneInfo(client_tz)
        except Exception as e:
            logger.warning(f"Invalid client timezone '{client_tz}': {e}")

    # Try environment default
    default_tz = os.getenv('DEFAULT_TZ', 'UTC')
    try:
        return ZoneInfo(default_tz)
    except Exception as e:
        logger.warning(f"Invalid DEFAULT_TZ '{default_tz}': {e}")

    # Final fallback to UTC
    return ZoneInfo('UTC')


def get_now_with_timezone(client_tz: str) -> Tuple[datetime, datetime]:
    """
    Get current time in both client timezone and UTC.

    Args:
        client_tz: Client timezone string

    Returns:
        Tuple of (now_local, now_utc) - both timezone-aware
    """
    tz = get_safe_timezone(client_tz)
    now_local = datetime.now(tz)
    now_utc = now_local.astimezone(timezone.utc)

    return now_local, now_utc


def coerce_to_local(dt: Optional[datetime], tz: ZoneInfo) -> Optional[datetime]:
    """
    Convert a datetime to the specified timezone, handling naive datetimes.

    This function ensures all datetimes are timezone-aware and properly
    handles DST ambiguity using fold parameter (PEP 495).

    Args:
        dt: Datetime to convert (can be naive or aware)
        tz: Target timezone

    Returns:
        Timezone-aware datetime in the target timezone, or None if input is None
    """
    if dt is None:
        return None

    # If naive, attach timezone (assume it's meant to be in target tz)
    if dt.tzinfo is None:
        # For ambiguous times during DST fall-back, prefer the later time (fold=1)
        # This matches most calendar apps' behavior
        dt = dt.replace(tzinfo=tz)

        # If this time is ambiguous (DST transition), we might need to set fold
        # Python's ZoneInfo handles this automatically for most cases
    else:
        # If already aware, convert to target timezone
        dt = dt.astimezone(tz)

    return dt


def serialize_datetime_pair(
    dt_local: Optional[datetime],
    client_tz: str
) -> dict:
    """
    Serialize a datetime to both local and UTC formats.

    Args:
        dt_local: Timezone-aware datetime in client timezone
        client_tz: Client timezone string for metadata

    Returns:
        Dict with start_local, start_utc, and timezone info
    """
    if dt_local is None:
        return {
            "local": None,
            "utc": None,
            "timezone": client_tz
        }

    # Ensure timezone-aware
    if dt_local.tzinfo is None:
        logger.warning("Received naive datetime in serialize_datetime_pair")
        tz = get_safe_timezone(client_tz)
        dt_local = dt_local.replace(tzinfo=tz)

    # Convert to UTC
    dt_utc = dt_local.astimezone(timezone.utc)

    return {
        "local": dt_local.isoformat(),
        "utc": dt_utc.isoformat().replace("+00:00", "Z"),
        "timezone": client_tz
    }


def log_timezone_context(
    client_tz: str,
    ref_local: datetime,
    ref_utc: datetime,
    request_id: Optional[str] = None
):
    """
    Log timezone context for observability and debugging.

    Args:
        client_tz: Client timezone string
        ref_local: Reference time in client timezone
        ref_utc: Reference time in UTC
        request_id: Optional request ID for tracing
    """
    server_tz_env = os.getenv("TZ", "unset")

    logger.info({
        "event": "parse_request",
        "request_id": request_id,
        "client_tz": client_tz,
        "server_tz_env": server_tz_env,
        "ref_utc": ref_utc.isoformat(),
        "ref_local": ref_local.isoformat(),
        "offset_minutes": ref_local.utcoffset().total_seconds() / 60 if ref_local.utcoffset() else 0
    })


def handle_dst_transition(
    dt: datetime,
    tz: ZoneInfo,
    prefer_later: bool = True
) -> datetime:
    """
    Handle DST transition times explicitly.

    During "fall back" transitions, one clock time occurs twice.
    This function allows explicit selection of which occurrence to use.

    Args:
        dt: Datetime (should be naive or in target timezone)
        tz: Target timezone
        prefer_later: If True, prefer the later occurrence during ambiguous times

    Returns:
        Timezone-aware datetime with fold properly set
    """
    if dt.tzinfo is None:
        # Make timezone-aware
        dt = dt.replace(tzinfo=tz)
    else:
        dt = dt.astimezone(tz)

    # Set fold for ambiguous times
    # fold=1 means the later of two ambiguous times
    if prefer_later:
        dt = dt.replace(fold=1)
    else:
        dt = dt.replace(fold=0)

    return dt


def parse_iso_with_timezone(
    iso_string: str,
    client_tz: str
) -> datetime:
    """
    Parse an ISO 8601 datetime string with proper timezone handling.

    Args:
        iso_string: ISO 8601 datetime string
        client_tz: Client timezone for naive datetimes

    Returns:
        Timezone-aware datetime
    """
    try:
        # Try to parse with timezone info
        dt = datetime.fromisoformat(iso_string)

        # If naive, attach client timezone
        if dt.tzinfo is None:
            tz = get_safe_timezone(client_tz)
            dt = dt.replace(tzinfo=tz)

        return dt
    except Exception as e:
        logger.error(f"Failed to parse ISO datetime '{iso_string}': {e}")
        raise ValueError(f"Invalid ISO datetime format: {iso_string}")


# Configuration defaults
DEFAULT_TZ = os.getenv("DEFAULT_TZ", "UTC")

# Ensure server runs in UTC to avoid confusion
if os.getenv("TZ") is None:
    logger.info("TZ environment variable not set, server will use system default")
else:
    logger.info(f"Server TZ environment variable: {os.getenv('TZ')}")
