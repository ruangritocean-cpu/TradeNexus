import pandas as pd
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def evaluate_candle_outcome(
    direction: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float,
    high: float,
    low: float,
    close: float
) -> tuple[str, float]:
    """
    Evaluates a single candle for TP/SL hits.
    
    Conservative Same-Candle Rule:
    If both TP and SL are touched in the same candle, always assume SL was hit first.
    
    Returns:
        tuple[str, float]: (outcome_status, realized_r_multiple)
    """
    risk = abs(entry - sl)
    if risk == 0:
        return "NO_OUTCOME", 0.0
        
    # Calculate target reward increments
    rr_tp1 = abs(tp1 - entry) / risk if risk > 0 else 1.5
    rr_tp2 = abs(tp2 - entry) / risk if risk > 0 else 2.0
    
    if "BUY" in direction:
        # Check SL and TP in same candle (SL-first conservative)
        sl_hit = (low <= sl)
        tp1_hit = (high >= tp1)
        tp2_hit = (high >= tp2)
        
        if sl_hit and (tp1_hit or tp2_hit):
            return "SL_HIT", -1.0  # Conservative same-candle SL-first
            
        if sl_hit:
            return "SL_HIT", -1.0
            
        if tp2_hit:
            return "TP2_HIT", rr_tp2
            
        if tp1_hit:
            return "TP1_HIT", rr_tp1
            
    elif "SELL" in direction:
        sl_hit = (high >= sl)
        tp1_hit = (low <= tp1)
        tp2_hit = (low <= tp2)
        
        if sl_hit and (tp1_hit or tp2_hit):
            return "SL_HIT", -1.0
            
        if sl_hit:
            return "SL_HIT", -1.0
            
        if tp2_hit:
            return "TP2_HIT", rr_tp2
            
        if tp1_hit:
            return "TP1_HIT", rr_tp1
            
    return "NO_OUTCOME", 0.0

def evaluate_signal_outcome(
    df: pd.DataFrame,
    entry_time: pd.Timestamp,
    direction: str,
    entry: float,
    sl: float,
    tp1: float,
    tp2: float,
    max_bars: int = 100
) -> dict:
    """
    Evaluates signal outcome sequentially over subsequent historical candles.
    """
    if df.empty or entry_time not in df.index:
        return {
            "status": "OPEN",
            "outcome_time": None,
            "bars_to_outcome": 0,
            "realized_r_multiple": 0.0
        }
        
    # Filter data starting *after* the entry candle close
    future_df = df.loc[df.index > entry_time].head(max_bars)
    
    if future_df.empty:
        return {
            "status": "OPEN",
            "outcome_time": None,
            "bars_to_outcome": 0,
            "realized_r_multiple": 0.0
        }
        
    risk = abs(entry - sl)
    
    bars_elapsed = 0
    for timestamp, row in future_df.iterrows():
        bars_elapsed += 1
        status, r_mult = evaluate_candle_outcome(
            direction=direction,
            entry=entry,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            high=row["High"],
            low=row["Low"],
            close=row["Close"]
        )
        
        if status in ["SL_HIT", "TP1_HIT", "TP2_HIT"]:
            return {
                "status": status,
                "outcome_time": timestamp.isoformat(),
                "bars_to_outcome": bars_elapsed,
                "realized_r_multiple": r_mult
            }
            
    # If we reached the end of future_df and it is the end of the main dataset:
    # Check if max_bars was fully exhausted
    if len(future_df) >= max_bars:
        # Calculate close-based R multiple at expiration
        last_row = future_df.iloc[-1]
        last_close = last_row["Close"]
        last_time = future_df.index[-1]
        
        if risk > 0:
            if "BUY" in direction:
                expired_r = (last_close - entry) / risk
            else:
                expired_r = (entry - last_close) / risk
        else:
            expired_r = 0.0
            
        return {
            "status": "EXPIRED",
            "outcome_time": last_time.isoformat(),
            "bars_to_outcome": max_bars,
            "realized_r_multiple": expired_r
        }
        
    # If the main dataset hasn't finished (still active candle), mark as OPEN
    return {
        "status": "OPEN",
        "outcome_time": None,
        "bars_to_outcome": 0,
        "realized_r_multiple": 0.0
    }
