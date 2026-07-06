import pytest
from tradenexus.signals.scoring import calculate_confluence_score

def test_regime_scoring_modifiers():
    """
    Verifies that the Confluence 2.0 scoring algorithm applies modifiers correctly
    for Sideways regimes, High Volatility, and Fallback SMC sources.
    """
    # 1. Base strong setup data
    base_data = {
        "CDC_Trend": "Bullish",
        "SuperTrend_Direction": "Bullish",
        "MACD_Trend": "Bullish",
        "Adaptive_Trend": "Bullish",
        "ADX": 30.0,
        "Support_Source": "CONFIRMED_SWING",
        "primary_regime": "TRENDING_UP",
        "regime_score": 80.0,
        "regime_flags": "",
        "Volume_Warning": "",
        "Volume_Confirmation": "BULLISH",
        "Close": 100.0,
        "VWAP": 95.0,
        "RR_TP1": 2.0
    }
    
    score_trending = calculate_confluence_score(base_data)
    assert score_trending["confluence_score"] > 80.0
    
    # 2. Modify regime to SIDEWAYS -> quality score and confluence score should drop
    sideways_data = base_data.copy()
    sideways_data["primary_regime"] = "SIDEWAYS"
    score_sideways = calculate_confluence_score(sideways_data)
    assert score_sideways["quality_score"] < score_trending["quality_score"]
    
    # 3. Add HIGH_VOLATILITY flag -> warning should be added, score should drop
    high_vol_data = base_data.copy()
    high_vol_data["regime_flags"] = "HIGH_VOLATILITY"
    score_high_vol = calculate_confluence_score(high_vol_data)
    assert score_high_vol["quality_score"] < score_trending["quality_score"]
    assert any("volatility" in w.lower() for w in score_high_vol["warnings"])
    
    # 4. Modify SMC source to FALLBACK -> score should drop
    fallback_data = base_data.copy()
    fallback_data["Support_Source"] = "FALLBACK"
    score_fallback = calculate_confluence_score(fallback_data)
    assert score_fallback["quality_score"] < score_trending["quality_score"]

def test_regime_decision_overrides():
    """
    Verifies that the regime decision rules override ENTRY TRIGGERED to WATCH
    under SQUEEZE or LOW_LIQUIDITY conditions.
    """
    from tradenexus.signals.rules import apply_regime_decision_rules
    
    # 1. Squeeze override
    final_state, reasons, warnings = apply_regime_decision_rules(
        decision_state="ENTRY TRIGGERED",
        primary_regime="SQUEEZE",
        flags=[],
        confluence_score=85.0
    )
    assert final_state == "WATCH"
    assert any("squeeze" in w.lower() for w in warnings)
    
    # 2. Low Liquidity override
    final_state_ll, reasons_ll, warnings_ll = apply_regime_decision_rules(
        decision_state="ENTRY TRIGGERED",
        primary_regime="TRENDING_UP",
        flags=["LOW_LIQUIDITY"],
        confluence_score=85.0
    )
    assert final_state_ll == "WATCH"
    assert any("liquidity" in w.lower() for w in warnings_ll)
