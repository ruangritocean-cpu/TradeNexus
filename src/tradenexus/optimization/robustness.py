from typing import Dict, Any, Tuple

def calculate_robustness_score(
    in_sample_metrics: Dict[str, Any],
    out_sample_metrics: Dict[str, Any],
    parameter_stability: float = 100.0,
    total_oos_trades: int = 0
) -> Tuple[float, str]:
    """
    Computes a robustness score (0-100) and maps a parameter recommendation status.
    Penalizes overfitting (in-to-out sample degradation), small sample size, and high drawdown.
    """
    # Fallback default values
    is_expectancy = in_sample_metrics.get("expectancy", 0.0)
    is_pf = in_sample_metrics.get("profit_factor", 1.0)
    is_dd = in_sample_metrics.get("max_drawdown", 0.0)
    
    oos_expectancy = out_sample_metrics.get("expectancy", 0.0)
    oos_pf = out_sample_metrics.get("profit_factor", 1.0)
    oos_win_rate = out_sample_metrics.get("win_rate", 0.0)
    oos_dd = out_sample_metrics.get("max_drawdown", 0.0)
    
    # 1. Base OOS Performance Score (max 80 points)
    # A. Expectancy Contribution (max 30 points)
    if oos_expectancy >= 0.5:
        exp_score = 30.0
    elif oos_expectancy > 0.0:
        exp_score = 15.0 + 30.0 * oos_expectancy
    else:
        exp_score = 0.0
        
    # B. Profit Factor Contribution (max 30 points)
    if oos_pf >= 2.0:
        pf_score = 30.0
    elif oos_pf >= 1.0:
        pf_score = 15.0 + 15.0 * (oos_pf - 1.0)
    else:
        pf_score = 0.0
        
    # C. Win Rate Contribution (max 20 points)
    win_score = min(20.0, 20.0 * (oos_win_rate / 50.0)) if oos_win_rate > 0 else 0.0
    
    base_score = exp_score + pf_score + win_score
    
    # 2. Stability Contribution (max 20 points)
    stability_contrib = 20.0 * (parameter_stability / 100.0)
    
    final_score = base_score + stability_contrib
    
    # 3. Penalties
    # A. Degradation Penalty (penalize if OOS expectancy is much worse than IS expectancy)
    degradation = is_expectancy - oos_expectancy
    if degradation > 0 and is_expectancy > 0:
        degradation_ratio = degradation / is_expectancy
        penalty = min(30.0, 30.0 * degradation_ratio)
        final_score -= penalty
        
    # B. Drawdown Penalty (penalize if OOS drawdown is 50% larger than IS drawdown)
    if oos_dd > 0 and is_dd > 0:
        dd_ratio = oos_dd / is_dd
        if dd_ratio > 1.5:
            final_score -= 15.0
            
    # C. Sample Size Penalty (extremely critical)
    if total_oos_trades < 5:
        final_score -= 80.0
    elif total_oos_trades < 10:
        final_score -= 40.0
    elif total_oos_trades < 15:
        final_score -= 20.0
        
    # Clamp final score between 0.0 and 100.0
    final_score = max(0.0, min(100.0, final_score))
    
    # 4. Determine Recommendation Status
    if total_oos_trades < 5:
        status = "REJECTED_INSUFFICIENT_DATA"
    elif oos_pf < 1.0 or oos_expectancy < 0:
        status = "REJECTED_POOR_OOS"
    elif total_oos_trades < 15:
        status = "WARNING_LOW_SAMPLE"
    elif parameter_stability < 50.0:
        status = "WARNING_UNSTABLE"
    elif final_score >= 60.0:
        status = "RECOMMENDED"
    else:
        status = "REJECTED_POOR_OOS"
        
    return final_score, status
