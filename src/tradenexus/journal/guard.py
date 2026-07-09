import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def parse_timeframe_delta(timeframe: str) -> datetime.timedelta:
    """
    Parses a timeframe string (15m, 1h, 4h, 1d) into a datetime.timedelta.
    """
    tf = timeframe.lower().strip()
    if tf == "15m":
        return datetime.timedelta(minutes=15)
    elif tf == "1h":
        return datetime.timedelta(hours=1)
    elif tf == "4h":
        return datetime.timedelta(hours=4)
    elif tf == "1d":
        return datetime.timedelta(days=1)
    else:
        # Default fallback
        return datetime.timedelta(minutes=15)

def is_candle_closed(
    candle_time: datetime.datetime, 
    timeframe: str, 
    now: Optional[datetime.datetime] = None, 
    mode: str = "live"
) -> bool:
    """
    Closed Candle Guard.
    
    In live mode:
    - Returns True only if the candle has fully closed (now >= candle_time + timeframe_duration).
    
    In backtest mode:
    - Returns True (all historical bars in the backtest dataset are treated as closed).
    """
    if mode == "backtest":
        return True
        
    # Ensure timezone alignment between now and candle_time
    if hasattr(candle_time, "tzinfo") and candle_time.tzinfo is not None:
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)
        # Align now to candle_time timezone
        now = now.astimezone(candle_time.tzinfo)
    else:
        if now is None:
            now = datetime.datetime.now()
            
    delta = parse_timeframe_delta(timeframe)
    close_time = candle_time + delta
    
    # If current time is past the candle's close time, it is closed
    return now >= close_time
