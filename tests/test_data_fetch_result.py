import pytest
import pandas as pd
from tradenexus.data.providers import DataFetchResult

def test_data_fetch_result_properties():
    df = pd.DataFrame({"open": [1.0], "close": [1.1]})
    res = DataFetchResult(
        df=df,
        provider_used="yfinance",
        fallback_used=0,
        data_quality_status="VALID",
        quality_score=95.0,
        warnings=["Warmup warning"],
        errors=[],
        latest_candle_time="2026-07-09T00:00:00Z",
        bars_available=1
    )
    
    assert res.provider_used == "yfinance"
    assert res.fallback_used == 0
    assert res.data_quality_status == "VALID"
    assert res.quality_score == 95.0
    assert len(res.warnings) == 1
    assert len(res.errors) == 0
    assert res.latest_candle_time == "2026-07-09T00:00:00Z"
    assert res.bars_available == 1
    assert not res.df.empty
