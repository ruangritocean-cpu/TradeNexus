import pytest
import pandas as pd
import numpy as np
from tradenexus.regime.classifier import classify_market_regime

def test_regime_classification_trending_up():
    """
    Verifies trending up classification under strong ADX and bullish EMA alignment.
    """
    df = pd.DataFrame({
        "ADX": [30.0] * 40,
        "ATR": [1.5] * 40,
        "EMA_Fast": [105.0] * 40,
        "EMA_Slow": [100.0] * 40,
        "Close": [106.0] * 40
    })
    res = classify_market_regime(df)
    assert res["primary_regime"] == "TRENDING_UP"
    assert res["regime_score"] > 50

def test_regime_classification_sideways():
    """
    Verifies sideways classification under low ADX.
    """
    df = pd.DataFrame({
        "ADX": [15.0] * 40,
        "ATR": [1.0] * 40,
        "EMA_Fast": [100.0] * 40,
        "EMA_Slow": [100.0] * 40,
        "Close": [100.0] * 40
    })
    res = classify_market_regime(df)
    assert res["primary_regime"] == "SIDEWAYS"

def test_regime_insufficient_data():
    """
    Verifies that short datasets return UNKNOWN with the INSUFFICIENT_DATA flag.
    """
    df = pd.DataFrame({
        "Close": [10.0] * 10
    })
    res = classify_market_regime(df)
    assert res["primary_regime"] == "UNKNOWN"
    assert "INSUFFICIENT_DATA" in res["flags"]
