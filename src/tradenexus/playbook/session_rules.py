import datetime
from typing import List, Tuple

SESSION_HOURS = {
    "ASIAN": (0, 9),
    "LONDON": (8, 17),
    "NEWYORK": (13, 22)
}

def get_current_sessions(time_utc: datetime.datetime = None) -> List[str]:
    """
    Returns list of active session names based on the hour.
    """
    if time_utc is None:
        time_utc = datetime.datetime.utcnow()
    hour = time_utc.hour
    
    active = []
    for session, (start, end) in SESSION_HOURS.items():
        if start <= hour <= end:
            active.append(session)
    return active

def validate_session_rule(allowed_sessions: List[str], current_time_utc: datetime.datetime = None) -> Tuple[bool, str]:
    """
    Checks if current UTC time matches one of the allowed sessions.
    """
    if not allowed_sessions:
        return True, "No session restrictions configured."
        
    active_sessions = get_current_sessions(current_time_utc)
    if not active_sessions:
        return False, "Current time is outside all recognized trading sessions (Asia/London/NY)."
        
    allowed_upper = [s.upper() for s in allowed_sessions]
    overlap = [s for s in active_sessions if s in allowed_upper]
    if overlap:
        return True, f"Active session matches allowed sessions: {', '.join(overlap)}"
    
    return False, f"Current active sessions ({', '.join(active_sessions)}) are not allowed by the playbook."
