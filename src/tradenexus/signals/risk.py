import logging

logger = logging.getLogger(__name__)

def validate_trade_risk(
    price: float, 
    decision: str, 
    support: float, 
    resistance: float, 
    atr: float, 
    rr_min: float = 1.5
) -> dict:
    """
    Risk Engine Veto Logic.
    
    Calculates entry, stop loss, and take profit targets:
    - BUY: SL = min(support - ATR buffer, entry - ATR multiple)
    - SELL: SL = max(resistance + ATR buffer, entry + ATR multiple)
    
    Verifies that target TP1 achieves a risk-to-reward ratio of at least rr_min.
    If not, vetoes the trade and overrides the final decision to 'NO TRADE'.
    """
    if decision == "NEUTRAL" or not ("BUY" in decision or "SELL" in decision):
        return {
            "Decision": "NEUTRAL",
            "Entry": price,
            "StopLoss": 0.0,
            "TakeProfit1": 0.0,
            "TakeProfit2": 0.0,
            "Risk": 0.0,
            "Reward_TP1": 0.0,
            "Reward_TP2": 0.0,
            "RR_TP1": 0.0,
            "RR_TP2": 0.0,
            "Vetoed": False,
            "VetoReason": ""
        }

    sl = 0.0
    tp1 = 0.0
    tp2 = 0.0
    vetoed = False
    veto_reason = ""
    
    atr_buffer = 1.5 * atr if atr > 0 else price * 0.015
    atr_multiple = 2.0 * atr if atr > 0 else price * 0.02
    
    if "BUY" in decision:
        # SL calculation
        sl_structural = support - atr_buffer if support > 0 else 0.0
        sl_atr = price - atr_multiple
        
        if sl_structural > 0 and sl_structural < price:
            sl = min(sl_structural, sl_atr)
        else:
            sl = sl_atr
            
        if sl <= 0 or (price - sl) < (price * 0.001):
            sl = price - (1.5 * (atr if atr > 0 else price * 0.01))
            
        risk = price - sl
        tp1 = price + (risk * rr_min)
        tp2 = price + (risk * 2.0)
        
        if resistance > price:
            tp2 = max(resistance, tp2)
            
        # Veto rule: check if major resistance blocks TP1 target (RR < rr_min)
        if resistance > price and (resistance - price) < (risk * rr_min):
            vetoed = True
            veto_reason = f"RR below minimum threshold: Major resistance at ${resistance:,.2f} is too close (blocks TP1 target)."
            
    elif "SELL" in decision:
        # SL calculation
        sl_structural = resistance + atr_buffer if resistance > 0 else 0.0
        sl_atr = price + atr_multiple
        
        if sl_structural > price:
            sl = max(sl_structural, sl_atr)
        else:
            sl = sl_atr
            
        if (sl - price) < (price * 0.001):
            sl = price + (1.5 * (atr if atr > 0 else price * 0.01))
            
        risk = sl - price
        tp1 = price - (risk * rr_min)
        tp2 = price - (risk * 2.0)
        
        if support < price and support > 0:
            tp2 = min(support, tp2)
            
        # Veto rule: check if major support blocks TP1 target (RR < rr_min)
        if support > 0 and support < price and (price - support) < (risk * rr_min):
            vetoed = True
            veto_reason = f"RR below minimum threshold: Major support at ${support:,.2f} is too close (blocks TP1 target)."
            
    # Calculate rewards and ratios
    risk_points = price - sl if "BUY" in decision else sl - price
    reward_tp1 = tp1 - price if "BUY" in decision else price - tp1
    reward_tp2 = tp2 - price if "BUY" in decision else price - tp2
    
    rr_tp1 = (reward_tp1 / risk_points) if risk_points > 0 else 0.0
    rr_tp2 = (reward_tp2 / risk_points) if risk_points > 0 else 0.0
    
    # Trigger Veto if calculated RR is below the minimum threshold directly
    if rr_tp1 < rr_min:
        vetoed = True
        veto_reason = f"RR below minimum threshold: Calculated TP1 RR is {rr_tp1:.2f} (min required: {rr_min})."
        
    final_decision = "NO TRADE" if vetoed else decision
    
    return {
        "Decision": final_decision,
        "Entry": price,
        "StopLoss": sl,
        "TakeProfit1": tp1,
        "TakeProfit2": tp2,
        "Risk": risk_points,
        "Reward_TP1": reward_tp1,
        "Reward_TP2": reward_tp2,
        "RR_TP1": rr_tp1,
        "RR_TP2": rr_tp2,
        "Vetoed": vetoed,
        "VetoReason": veto_reason
    }
