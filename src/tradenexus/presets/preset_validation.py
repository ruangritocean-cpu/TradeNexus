from typing import Tuple, List
from tradenexus.presets.preset_models import StrategyPreset

def validate_preset(preset: StrategyPreset) -> Tuple[bool, List[str], List[str]]:
    """
    Validates StrategyPreset settings and constraints before saving/applying.
    Returns (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    # 1. Confluence Score
    if not (0.0 <= preset.min_confluence_score <= 100.0):
        errors.append(f"Confluence threshold ({preset.min_confluence_score}) must be between 0 and 100.")
        
    # 2. Risk-to-Reward Ratio
    if preset.min_rr < 1.0:
        errors.append(f"Minimum Risk-to-Reward Ratio ({preset.min_rr}) must be >= 1.0.")
    elif preset.min_rr > 5.0:
        warnings.append(f"Minimum Risk-to-Reward Ratio ({preset.min_rr}) is unusually high (above 5.0).")
        
    # 3. Allowed Sessions
    valid_sessions = {"ASIAN", "LONDON", "NEWYORK"}
    for s in preset.allowed_sessions:
        if s not in valid_sessions:
            errors.append(f"Session '{s}' is invalid. Allowed: ASIAN, LONDON, NEWYORK.")
            
    # 4. Timeframes
    valid_tfs = {"5m", "15m", "30m", "1h", "2h", "4h", "1d"}
    for tf in preset.allowed_timeframes:
        if tf not in valid_tfs:
            warnings.append(f"Timeframe '{tf}' might not be supported natively by all resampling providers.")
            
    # 5. Limits & Cooldowns
    if preset.max_trades_per_day < 0:
        errors.append("Maximum trades per day cannot be negative.")
    if preset.max_losses_per_day < 0:
        errors.append("Maximum losses per day cannot be negative.")
    if preset.max_consecutive_losses < 0:
        errors.append("Maximum consecutive losses cannot be negative.")
    if preset.cooldown_minutes_after_loss < 0:
        errors.append("Cooldown minutes cannot be negative.")
        
    # 6. Portfolio Risk Percentage
    if not (0.1 <= preset.default_portfolio_risk_pct <= 5.0):
        errors.append(f"Default portfolio risk per trade ({preset.default_portfolio_risk_pct}%) must be between 0.1% and 5.0%.")
    elif preset.default_portfolio_risk_pct > 3.0:
        warnings.append(f"Risk per trade ({preset.default_portfolio_risk_pct}%) is set high (above 3.0%). Exercise extreme caution.")
        
    # 7. Symbols format
    for sym in preset.allowed_symbols:
        if not isinstance(sym, str) or not sym.strip():
            errors.append("Allowed symbols list contains an invalid symbol entry.")
            
    is_valid = len(errors) == 0
    return is_valid, errors, warnings
