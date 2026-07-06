import pytest
import datetime
from tradenexus.journal.guard import is_candle_closed

def test_closed_candle_guard():
    """
    Verifies that the is_candle_closed guard detects open vs closed candles correctly
    based on current time and timeframe duration.
    """
    # 15m candle starting at 12:00:00 closes at 12:15:00
    candle_time = datetime.datetime(2026, 7, 6, 12, 0, 0)
    
    # 1. Test live mode - open candle (now is 12:10:00) -> should be False
    now_open = datetime.datetime(2026, 7, 6, 12, 10, 0)
    assert not is_candle_closed(candle_time, "15m", now_open, mode="live")
    
    # 2. Test live mode - closed candle (now is 12:15:00) -> should be True
    now_closed = datetime.datetime(2026, 7, 6, 12, 15, 0)
    assert is_candle_closed(candle_time, "15m", now_closed, mode="live")
    
    # 3. Test live mode - closed candle (now is 12:20:00) -> should be True
    now_after = datetime.datetime(2026, 7, 6, 12, 20, 0)
    assert is_candle_closed(candle_time, "15m", now_after, mode="live")
    
    # 4. Test backtest mode -> always True
    assert is_candle_closed(candle_time, "15m", now_open, mode="backtest")
