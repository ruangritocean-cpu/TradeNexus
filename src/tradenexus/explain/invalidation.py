import logging
from typing import List, Dict, Any
from tradenexus.explain.brief_models import BriefInvalidation

logger = logging.getLogger(__name__)

def generate_invalidation_conditions(data: Dict[str, Any]) -> List[BriefInvalidation]:
    """
    Deduces invalidation thresholds and rules for BUY or SELL setups.
    """
    conditions = []
    direction = data.get("direction", "NEUTRAL").upper()
    sl = data.get("sl", 0.0)
    
    # 1. SL breach check
    if sl > 0:
        if "BUY" in direction:
            conditions.append(BriefInvalidation(
                condition="Stop Loss Breach",
                price_level=sl,
                notes=f"If candle close breaks below Stop Loss at {sl:.4f}."
            ))
        elif "SELL" in direction:
            conditions.append(BriefInvalidation(
                condition="Stop Loss Breach",
                price_level=sl,
                notes=f"If candle close breaks above Stop Loss at {sl:.4f}."
            ))
            
    # 2. Support / Resistance level breach
    support = data.get("support_level", data.get("entry", 0.0) * 0.95)
    resistance = data.get("resistance_level", data.get("entry", 0.0) * 1.05)
    
    if "BUY" in direction and support > 0 and support != sl:
        conditions.append(BriefInvalidation(
            condition="Swing Support Failure",
            price_level=support,
            notes=f"If price loses local swing support structure at {support:.4f}."
        ))
    elif "SELL" in direction and resistance > 0 and resistance != sl:
        conditions.append(BriefInvalidation(
            condition="Swing Resistance Failure",
            price_level=resistance,
            notes=f"If price breaches local swing resistance structure at {resistance:.4f}."
        ))
        
    # 3. Market Regime changes
    conditions.append(BriefInvalidation(
        condition="Market Regime Shift",
        price_level=0.0,
        notes="If market structure shifts to SIDEWAYS / LOW_LIQUIDITY regime."
    ))
    
    # 4. Risk / Veto check
    if data.get("portfolio_risk_status", "OK") == "BLOCKED":
        conditions.append(BriefInvalidation(
            condition="Portfolio Risk Block",
            price_level=0.0,
            notes="Portfolio daily limits or open risk allocation thresholds exceeded."
        ))
        
    return conditions
