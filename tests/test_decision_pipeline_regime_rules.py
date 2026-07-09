import pytest
from tradenexus.signals.rules import apply_regime_decision_rules
from tradenexus.pipeline.decision_pipeline import evaluate_decision_and_scoring

def test_apply_regime_decision_rules_normalization():
    """
    Verifies that apply_regime_decision_rules handles string flags, None, and lists safely.
    """
    # 1. Test string flags (Low Liquidity)
    state, reasons, warnings = apply_regime_decision_rules(
        decision_state="ENTRY TRIGGERED",
        primary_regime="TRENDING_UP",
        flags="LOW_LIQUIDITY",
        confluence_score=85.0
    )
    assert state == "WATCH"  # LOW_LIQUIDITY blocks entry
    assert any("Low liquidity" in w for w in warnings)

    # 1b. Test string flags (High Volatility)
    state, reasons, warnings = apply_regime_decision_rules(
        decision_state="ENTRY TRIGGERED",
        primary_regime="TRENDING_UP",
        flags="HIGH_VOLATILITY",
        confluence_score=85.0
    )
    assert state == "ENTRY TRIGGERED"
    assert any("High volatility active" in w for w in warnings)

    # 2. Test flags=None
    state, reasons, warnings = apply_regime_decision_rules(
        decision_state="ENTRY TRIGGERED",
        primary_regime="SIDEWAYS",
        flags=None,
        confluence_score=75.0
    )
    assert state == "WATCH"  # Sideways blocks weak entry (75% < 80%)
    assert any("Sideways regime" in w for w in warnings)

    # 3. Test squeeze regime blocks entry
    state, reasons, warnings = apply_regime_decision_rules(
        decision_state="ENTRY TRIGGERED",
        primary_regime="SQUEEZE",
        flags=[],
        confluence_score=90.0
    )
    assert state == "WATCH"  # Squeeze blocks entry unconditionally
    assert any("Squeeze compression" in w for w in warnings)

    # 4. Test missing/default parameters (safely fallbacks)
    state, reasons, warnings = apply_regime_decision_rules("ENTRY TRIGGERED")
    assert state == "ENTRY TRIGGERED"
    assert len(reasons) == 0
    assert len(warnings) == 0

def test_evaluate_decision_and_scoring_missing_regime():
    """
    Verifies that evaluate_decision_and_scoring does not crash when regime keys are missing.
    """
    latest_15m = {"Close": 100.0, "CDC_Trend": "Bullish", "Support_Level": 95.0, "Resistance_Level": 105.0}
    latest_1h = {"Close": 100.0, "CDC_Trend": "Bullish", "Support_Level": 95.0, "Resistance_Level": 105.0}
    latest_4h = {"Close": 100.0, "CDC_Trend": "Bullish", "Support_Level": 95.0, "Resistance_Level": 105.0}
    latest_1d = {"Close": 100.0, "CDC_Trend": "Bullish", "Support_Level": 95.0, "Resistance_Level": 105.0}
    
    # Run pipeline evaluation - must succeed without raising errors
    res = evaluate_decision_and_scoring(
        latest_15m=latest_15m,
        latest_1h=latest_1h,
        latest_4h=latest_4h,
        latest_1d=latest_1d,
        timeframe="1h"
    )
    
    assert res["decision_state"] in ["NO TRADE", "WATCH", "READY", "ENTRY TRIGGERED"]
    assert res["primary_regime"] == "UNKNOWN"
    assert res["regime_flags"] == []
