import pytest
from tradenexus.explain.warning_summarizer import summarize_warnings

def test_warning_summarizer_empty():
    res = summarize_warnings([])
    assert res == ["No critical warnings."]

def test_warning_summarizer_sorting_and_dedup():
    raw = [
        "Low liquidity warning",
        "Daily risk limit breached",
        "High correlation warning",
        "Daily risk limit breached",  # duplicate
        "ATR volatility is high"
    ]
    
    res = summarize_warnings(raw)
    
    # Check deduplication
    assert len(res) == 4
    
    # Breach/limit warning should be sorted first (priority 0)
    assert "limit breached" in res[0].lower()
    
    # Correlation / liquidity warnings sorted next (priority 1)
    assert "liquidity" in res[1].lower() or "correlation" in res[1].lower()
