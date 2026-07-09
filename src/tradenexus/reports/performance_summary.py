from typing import List, Dict, Any

def calculate_performance_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates key performance metrics from a list of trades.
    """
    closed_trades = [t for t in trades if t.get("status") == "CLOSED" or t.get("closed_at") is not None]
    total_trades = len(trades)
    closed_count = len(closed_trades)
    
    if closed_count == 0:
        return {
            "trades_opened": total_trades,
            "trades_closed": 0,
            "win_rate": 0.0,
            "expectancy": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0
        }
        
    wins = 0
    losses = 0
    total_win_r = 0.0
    total_loss_r = 0.0
    total_r = 0.0
    
    for t in closed_trades:
        r = t.get("realized_r_multiple") or 0.0
        total_r += r
        if r > 0:
            wins += 1
            total_win_r += r
        else:
            losses += 1
            total_loss_r += abs(r)
            
    win_rate = wins / closed_count if closed_count > 0 else 0.0
    expectancy = total_r / closed_count if closed_count > 0 else 0.0
    
    # Profit factor: Total Win R / Total Loss R
    if total_loss_r == 0:
        profit_factor = total_win_r if total_win_r > 0 else 1.0
    else:
        profit_factor = total_win_r / total_loss_r
        
    # Calculate Max Drawdown based on R-multiple sequence
    # Sort trades by closed time or opened time (already sorted by opened_at in repo)
    sorted_trades = sorted(closed_trades, key=lambda x: x.get("closed_at") or x.get("opened_at") or "")
    
    cumulative_r = 0.0
    peak_r = 0.0
    max_dd = 0.0
    
    for t in sorted_trades:
        r = t.get("realized_r_multiple") or 0.0
        cumulative_r += r
        if cumulative_r > peak_r:
            peak_r = cumulative_r
        dd = peak_r - cumulative_r
        if dd > max_dd:
            max_dd = dd
            
    return {
        "trades_opened": total_trades,
        "trades_closed": closed_count,
        "win_rate": win_rate,
        "expectancy": expectancy,
        "profit_factor": profit_factor,
        "max_drawdown": max_dd
    }
