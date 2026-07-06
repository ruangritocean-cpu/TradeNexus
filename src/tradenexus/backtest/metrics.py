import numpy as np
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def calculate_backtest_metrics(trades: List[Dict]) -> Dict:
    """
    Calculates key performance metrics for a list of trade outcomes.
    
    Each trade dict should contain:
    - "status": str ("SL_HIT", "TP1_HIT", "TP2_HIT", "EXPIRED", etc.)
    - "realized_r_multiple": float
    - "bars_to_outcome": int
    """
    total_signals = len(trades)
    if total_signals == 0:
        return {
            "total_signals": 0,
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "average_r": 0.0,
            "max_drawdown": 0.0,
            "average_holding_bars": 0.0,
            "max_consecutive_losses": 0,
            "tp1_rate": 0.0,
            "tp2_rate": 0.0,
            "sl_rate": 0.0
        }
        
    wins = 0
    losses = 0
    tp1_hits = 0
    tp2_hits = 0
    sl_hits = 0
    expired_count = 0
    
    gross_wins = 0.0
    gross_losses = 0.0
    
    total_holding_bars = 0
    
    # Track consecutive losses
    current_consecutive_losses = 0
    max_consecutive_losses = 0
    
    # Build simple additive equity curve starting at 100R to calculate drawdown
    equity = 100.0
    peak = 100.0
    max_dd = 0.0
    
    # Filter trades that actually had an entry outcome (not ignored or open)
    resolved_trades = [t for t in trades if t.get("status") != "OPEN"]
    total_resolved = len(resolved_trades)
    
    if total_resolved == 0:
        # Return default zeroed dictionary if no resolved trades
        return {
            "total_signals": total_signals,
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "average_r": 0.0,
            "max_drawdown": 0.0,
            "average_holding_bars": 0.0,
            "max_consecutive_losses": 0,
            "tp1_rate": 0.0,
            "tp2_rate": 0.0,
            "sl_rate": 0.0
        }
        
    for t in resolved_trades:
        status = t.get("status", "EXPIRED")
        r = t.get("realized_r_multiple", 0.0)
        bars = t.get("bars_to_outcome", 0)
        
        total_holding_bars += bars
        
        # Calculate equity curve
        equity += r
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            
        # Count outcomes
        if status == "SL_HIT":
            sl_hits += 1
            losses += 1
            gross_losses += abs(r)
            current_consecutive_losses += 1
            if current_consecutive_losses > max_consecutive_losses:
                max_consecutive_losses = current_consecutive_losses
        elif "TP" in status:
            wins += 1
            gross_wins += r
            current_consecutive_losses = 0
            if status == "TP1_HIT":
                tp1_hits += 1
            elif status == "TP2_HIT":
                tp2_hits += 1
        elif status == "EXPIRED":
            expired_count += 1
            if r > 0:
                wins += 1
                gross_wins += r
                current_consecutive_losses = 0
            elif r < 0:
                losses += 1
                gross_losses += abs(r)
                current_consecutive_losses += 1
                if current_consecutive_losses > max_consecutive_losses:
                    max_consecutive_losses = current_consecutive_losses
            else:
                current_consecutive_losses = 0
                
    win_rate = (wins / total_resolved) * 100
    
    # Expectancy = Average R multiple
    total_r = sum(t.get("realized_r_multiple", 0.0) for t in resolved_trades)
    expectancy = total_r / total_resolved
    
    # Profit factor = gross wins / gross losses
    if gross_losses == 0.0:
        profit_factor = float('inf') if gross_wins > 0 else 1.0
    else:
        profit_factor = gross_wins / gross_losses
        
    avg_holding = total_holding_bars / total_resolved
    
    return {
        "total_signals": total_signals,
        "total_trades": total_resolved,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "average_r": expectancy,
        "max_drawdown": max_dd,
        "average_holding_bars": avg_holding,
        "max_consecutive_losses": max_consecutive_losses,
        "tp1_rate": (tp1_hits / total_resolved) * 100,
        "tp2_rate": (tp2_hits / total_resolved) * 100,
        "sl_rate": (sl_hits / total_resolved) * 100
    }
