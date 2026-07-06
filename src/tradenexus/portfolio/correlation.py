import datetime
import logging
import pandas as pd
import numpy as np
import threading
from typing import List, Dict, Any, Tuple
import yfinance as yf
from tradenexus.portfolio.risk_models import CorrelationRiskResult

logger = logging.getLogger(__name__)

# Global cache variables
_cache_lock = threading.Lock()
_correlation_cache: Dict[str, Any] = {}

def calculate_returns_correlation(
    symbols: List[str],
    lookback_bars: int = 50,
    correlation_threshold: float = 0.7,
    cache_ttl_seconds: int = 3600
) -> CorrelationRiskResult:
    """
    Computes a Pearson correlation matrix from watchlist symbol daily returns.
    Caches historical data downloads to avoid Yahoo Finance API limit penalties.
    """
    if not symbols:
        return CorrelationRiskResult({}, [], [], "No symbols provided.")
        
    symbols = sorted(list(set(symbols)))
    cache_key = ",".join(symbols) + f"_{lookback_bars}"
    now = datetime.datetime.now(datetime.timezone.utc)
    
    # 1. Try Loading from Cache
    with _cache_lock:
        if cache_key in _correlation_cache:
            cached = _correlation_cache[cache_key]
            expires = cached["timestamp"] + datetime.timedelta(seconds=cache_ttl_seconds)
            if now < expires:
                logger.info(f"Using cached correlation matrix for {symbols}")
                return cached["result"]
                
    # 2. Cache Miss: Fetch Data & Calculate correlation
    logger.info(f"Correlation cache miss. Downloading price history for correlation calculation: {symbols}")
    
    # Download daily history for lookback period (e.g. 50 bars requires ~75 days)
    days_to_download = max(int(lookback_bars * 1.5), 90)
    period = f"{days_to_download}d"
    
    price_data = {}
    
    for sym in symbols:
        try:
            df = yf.download(sym, period=period, interval="1d", progress=False, auto_adjust=True)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                price_data[sym] = df["Close"]
        except Exception as e:
            logger.warning(f"Failed to fetch daily correlation prices for {sym}: {str(e)}")
            
    if len(price_data) < 2:
        # Insufficient data
        empty_res = CorrelationRiskResult({}, [], [], "Insufficient asset price data for correlation.")
        return empty_res
        
    # Standardize index and merge
    df_prices = pd.DataFrame(price_data).dropna()
    if len(df_prices) < 5:
        return CorrelationRiskResult({}, [], [], "Insufficient overlapping date records.")
        
    # Calculate percentage daily returns
    df_returns = df_prices.pct_change().dropna()
    
    # Slice to lookback length
    df_returns = df_returns.iloc[-lookback_bars:]
    
    # Pearson correlation matrix
    corr_df = df_returns.corr(method="pearson")
    
    # Format to dict of dicts
    corr_matrix = corr_df.to_dict()
    
    # Identify highly correlated pairs
    highly_correlated = []
    same_dir_warnings = []
    cols = corr_df.columns
    
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            sym_a = cols[i]
            sym_b = cols[j]
            coeff = corr_df.iloc[i, j]
            if not np.isnan(coeff) and abs(coeff) >= correlation_threshold:
                highly_correlated.append((sym_a, sym_b, coeff))
                
    warning_str = ""
    if highly_correlated:
        pairs_desc = [f"{a}-{b} ({c:.2f})" for a, b, c in highly_correlated]
        warning_str = f"High correlation detected in watchlist assets: {', '.join(pairs_desc)}."
        
    result = CorrelationRiskResult(
        correlation_matrix=corr_matrix,
        highly_correlated_pairs=highly_correlated,
        same_direction_correlation_warnings=same_dir_warnings,
        correlation_warning=warning_str
    )
    
    # Save to Cache
    with _cache_lock:
        _correlation_cache[cache_key] = {
            "timestamp": now,
            "result": result
        }
        
    return result
