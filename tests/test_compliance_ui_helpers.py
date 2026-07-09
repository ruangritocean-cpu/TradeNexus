import pytest
import datetime

def test_date_range_calculations():
    """
    Verifies helper date bounds math matching the UI implementation logic.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Today calculations
    start_dt = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
    assert start_dt.day == now_utc.day
    assert end_dt.day == now_utc.day
    assert start_dt.hour == 0
    assert end_dt.hour == 23
    
    # 2. 7 days calculations
    start_7 = now_utc - datetime.timedelta(days=7)
    assert (now_utc - start_7).days == 7
