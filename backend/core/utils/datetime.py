from datetime import datetime, timezone

def get_utc_now() -> datetime:
    """Get current UTC datetime with timezone information"""
    return datetime.now(timezone.utc)
