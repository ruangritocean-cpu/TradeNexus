import pytest
from tradenexus.explain.reason_builder import build_reasons

def test_reason_builder_trend_following():
    data = {
        "market_bias": "Bullish",
        "setup_direction": "Bullish",
        "trigger_direction": "Bullish",
        "alignment_type": "TREND_FOLLOWING",
        "confluence_score": 85.0,
        "primary_regime": "TRENDING_UP",
        "regime_flags": ["HIGH_VOLATILITY"],
        "vwap_alignment": "BULLISH",
        "volume_confirmation": "BULLISH_VOLUME",
        "bos_present": 1,
        "choch_present": 0,
        "fvg_present": 1,
        "rr_tp1": 2.1
    }
    
    reasons = build_reasons(data)
    assert any("โครงสร้างแนวโน้มหลักสอดคล้องตรงกัน" in r for r in reasons)
    assert any("Confluence Score อยู่ที่ 85" in r for r in reasons)
    assert any("จัดอยู่ในประเภท: แนวโน้มขาขึ้น (TRENDING UP)" in r for r in reasons)
    assert any("อยู่เหนือเส้น VWAP (Bullish)" in r for r in reasons)
    assert any("BOS" in r for r in reasons)
    assert any("FVG" in r for r in reasons)
    assert any("Risk/Reward Ratio) อยู่ที่ 2.10" in r for r in reasons)

def test_reason_builder_conflicted():
    data = {
        "market_bias": "Bullish",
        "setup_direction": "Bearish",
        "alignment_type": "CONFLICTED",
        "confluence_score": 45.0,
        "primary_regime": "SIDEWAYS"
    }
    
    reasons = build_reasons(data)
    assert any("แนวโน้มขัดแย้งกันในแต่ละกรอบเวลาหลัก" in r for r in reasons)
    assert any("Confluence Score อยู่ที่ 45" in r for r in reasons)
