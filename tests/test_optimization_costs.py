import pytest
import pandas as pd
from tradenexus.optimization.optimizer import run_sandbox_backtest, calculate_metrics

def test_sandbox_backtest_costs():
    # Setup simple dataframes to simulate trades
    df_raw = pd.DataFrame({
        "Open": [100.0] * 200,
        "High": [105.0] * 200,
        "Low": [95.0] * 200,
        "Close": [101.0] * 200,
        "Volume": [1000] * 200,
        "CDC_Trend": ["Bullish"] * 200,
        "SuperTrend_Direction": ["Bullish"] * 200,
        "MACD_Trend": ["Bullish"] * 200,
        "Adaptive_Trend": ["Bullish"] * 200,
        "ADX": [30.0] * 200,
        "Support_Level": [95.0] * 200,
        "Support_Source": ["CONFIRMED_SWING"] * 200,
        "Resistance_Level": [105.0] * 200,
        "Resistance_Source": ["CONFIRMED_SWING"] * 200,
        "ATR": [2.0] * 200,
        "primary_regime": ["TRENDING_UP"] * 200,
        "regime_score": [80.0] * 200,
        "regime_flags": [""] * 200
    }, index=pd.date_range("2026-07-09 10:00:00", periods=200, freq="1h"))
    
    tf_dfs = {"15m": df_raw, "1h": df_raw, "4h": df_raw, "1d": df_raw}
    params = {"confluence_threshold": 70.0, "rr_threshold": 1.5, "max_bars_to_hold": 20}
    
    # 1. Gross results (no commission, no slippage)
    trades_gross = run_sandbox_backtest(tf_dfs, "BTC", "1h", params, slippage_points=0.0, commission_pct=0.0)
    
    # 2. Net results (with cost model)
    trades_net = run_sandbox_backtest(tf_dfs, "BTC", "1h", params, slippage_points=0.1, commission_pct=0.001)
    
    # Cost should deduct expectancy
    gross_metrics = calculate_metrics(trades_gross)
    net_metrics = calculate_metrics(trades_net)
    
    if trades_gross and trades_net:
        assert net_metrics["expectancy"] < gross_metrics["expectancy"]
