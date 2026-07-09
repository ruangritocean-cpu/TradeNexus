import pytest
import pandas as pd
from tradenexus.data.provider_interface import DataProvider
from tradenexus.data.provider_registry import register_provider, set_fallback_chain
from tradenexus.data.fallback_provider import execute_fallback_chain

class FailingProvider(DataProvider):
    @property
    def provider_name(self) -> str:
        return "failing"
        
    @property
    def supported_intervals(self):
        return ["1h"]
        
    def fetch_ohlcv(self, symbol, interval, period=None, start=None, end=None):
        raise ValueError("API connection failed")
        
    def health_check(self):
        return False

class HealthyProvider(DataProvider):
    @property
    def provider_name(self) -> str:
        return "healthy"
        
    @property
    def supported_intervals(self):
        return ["1h"]
        
    def fetch_ohlcv(self, symbol, interval, period=None, start=None, end=None):
        dates = pd.date_range("2026-07-09 00:00:00", periods=110, freq="h", tz="UTC")
        df = pd.DataFrame({
            "open": [10.0] * 110,
            "high": [11.0] * 110,
            "low": [9.0] * 110,
            "close": [10.5] * 110,
            "volume": [100.0] * 110,
            "timestamp": [x.isoformat() for x in dates],
            "provider": "healthy",
            "symbol": symbol,
            "interval": interval
        }, index=dates)
        return df
        
    def health_check(self):
        return True

def test_fallback_trigger_on_failure():
    failing = FailingProvider()
    healthy = HealthyProvider()
    
    register_provider(failing)
    register_provider(healthy)
    
    set_fallback_chain(["failing", "healthy"])
    
    df, report = execute_fallback_chain("BTC-USD", "1h")
    
    assert not df.empty
    assert report["provider_used"] == "healthy"
    assert report["fallback_used"] == 1
    assert report["data_quality_status"] == "VALID"
