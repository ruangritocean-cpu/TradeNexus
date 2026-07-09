import datetime
from tradenexus.data.quality import check_stale_candle

def test_stale_thresholds():
    # Wednesday test reference
    non_weekend_wed = datetime.datetime(2026, 7, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
    
    # 1. Equities daily candle 4 days ago on Wednesday -> Stale
    last_daily = non_weekend_wed - datetime.timedelta(days=4)
    stale_eq, msg_eq = check_stale_candle(last_daily, "1d", "EQUITIES", current_time_utc=non_weekend_wed)
    assert stale_eq is True
    
    # 2. Equities checked on weekend -> Market closed, not stale
    weekend_sat = datetime.datetime(2026, 7, 11, 12, 0, 0, tzinfo=datetime.timezone.utc)
    last_friday = weekend_sat - datetime.timedelta(days=1)
    stale_sat, msg_sat = check_stale_candle(last_friday, "1d", "EQUITIES", current_time_utc=weekend_sat)
    assert stale_sat is False
    
    # 3. Crypto checked on weekend -> 24/7 market, daily 4 days ago is stale
    stale_crypto, msg_crypto = check_stale_candle(last_daily, "1d", "CRYPTO", current_time_utc=weekend_sat)
    assert stale_crypto is True
