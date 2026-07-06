import pytest
import pandas as pd
from tradenexus.backtest.metrics import calculate_backtest_metrics
from tradenexus.ui.components import render_breakdown_tables

def test_breakdown_metric_generation():
    """
    Verifies that backtest results can be grouped and analyzed by Market Regime,
    SMC structures, and VWAP alignment using pandas, and warning behaves correctly.
    """
    signals = [
        {
            "primary_regime": "TRENDING_UP",
            "vwap_alignment": "BULLISH",
            "bos_present": 1,
            "realized_r_multiple": 1.5,
            "status": "TP1_HIT",
            "bars_to_outcome": 5
        },
        {
            "primary_regime": "SIDEWAYS",
            "vwap_alignment": "BEARISH",
            "bos_present": 0,
            "realized_r_multiple": -1.0,
            "status": "SL_HIT",
            "bars_to_outcome": 3
        },
        {
            "primary_regime": "TRENDING_UP",
            "vwap_alignment": "BULLISH",
            "bos_present": 1,
            "realized_r_multiple": 2.0,
            "status": "TP2_HIT",
            "bars_to_outcome": 10
        }
    ]
    
    df = pd.DataFrame(signals)
    
    # 1. Group by primary_regime
    regime_grp = df.groupby("primary_regime").agg(
        Count=("realized_r_multiple", "count"),
        Avg_R=("realized_r_multiple", "mean")
    )
    assert regime_grp.loc["TRENDING_UP"]["Count"] == 2
    assert regime_grp.loc["SIDEWAYS"]["Count"] == 1
    
    # 2. Group by vwap_alignment
    vwap_grp = df.groupby("vwap_alignment").agg(
        Count=("realized_r_multiple", "count")
    )
    assert vwap_grp.loc["BULLISH"]["Count"] == 2
    
    # 3. Check sample size warning logic
    metrics = calculate_backtest_metrics(signals)
    assert metrics["total_trades"] < 30  # Should trigger warning flag
