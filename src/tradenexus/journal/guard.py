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
        
    # Standardize both candle_time and now to timezone-naive UTC for comparison
    if hasattr(candle_time, "tzinfo") and candle_time.tzinfo is not None:
        # Normalize to UTC and strip timezone info
        if hasattr(candle_time, "to_pydatetime"):
            candle_dt = candle_time.to_pydatetime()
        else:
            candle_dt = candle_time
            
        candle_utc = candle_dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        
        if now is None:
            now_dt = datetime.datetime.now(datetime.timezone.utc)
        else:
            now_dt = now.astimezone(datetime.timezone.utc)
        now_utc = now_dt.replace(tzinfo=None)
    else:
        # Both naive
        candle_utc = candle_time
        if now is None:
            now_utc = datetime.datetime.now()
        else:
            now_utc = now
            if now_utc.tzinfo is not None:
                now_utc = now_utc.astimezone(datetime.timezone.utc).replace(tzinfo=None)
                
    delta = parse_timeframe_delta(timeframe)
    close_time = candle_utc + delta
    
    # Compare naive UTC times
    return now_utc >= close_time
