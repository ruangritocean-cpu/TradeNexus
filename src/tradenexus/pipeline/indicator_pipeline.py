import logging
import pandas as pd
import numpy as np
from tradenexus.indicators.trend import calculate_cdc_actionzone, calculate_adaptive_trend
from tradenexus.indicators.momentum import calculate_macd, calculate_adx
from tradenexus.indicators.volatility import calculate_bollinger_bands
from tradenexus.indicators.smc import calculate_smc_lite
from tradenexus.indicators.mcdx import calculate_mcdx_proxy
from tradenexus.indicators.volume import calculate_volume_indicators
from tradenexus.indicators.structure import calculate_smc_structures
from tradenexus.indicators.liquidity import calculate_liquidity_zones
from tradenexus.regime.classifier import classify_market_regime

logger = logging.getLogger(__name__)

def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Unified indicator pipeline. Applies all Technical, SMC, Volume, and Regime calculations.
    """
    if df.empty:
        return df
        
    df = df.copy()
    
    # 1. Base Indicators
    df = calculate_cdc_actionzone(df)
    df = calculate_macd(df)
    df = calculate_smc_lite(df)
    df = calculate_mcdx_proxy(df)
    df = calculate_adaptive_trend(df)
    df = calculate_bollinger_bands(df)
    df = calculate_adx(df)
    df = calculate_volume_indicators(df)
    
    # 2. SMC Structures & Liquidity Zones
    df = calculate_smc_structures(df)
    df = calculate_liquidity_zones(df)
    
    # 3. Market Regime classification (Rolling optimized for last 5 rows)
    primary_regimes = ["UNKNOWN"] * len(df)
    regime_scores = [0.0] * len(df)
    regime_flags_list = [""] * len(df)
    
    start_idx = max(0, len(df) - 5)
    for idx in range(start_idx, len(df)):
        sub_df = df.iloc[:idx+1]
        reg_res = classify_market_regime(sub_df)
        primary_regimes[idx] = reg_res["primary_regime"]
        regime_scores[idx] = reg_res["regime_score"]
        regime_flags_list[idx] = ",".join(reg_res["flags"])
        
    df["primary_regime"] = primary_regimes
    df["regime_score"] = regime_scores
    df["regime_flags"] = regime_flags_list
    
    return df
