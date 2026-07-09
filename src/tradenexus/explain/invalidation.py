import logging
from typing import List, Dict, Any
from tradenexus.explain.brief_models import BriefInvalidation

logger = logging.getLogger(__name__)

def generate_invalidation_conditions(data: Dict[str, Any]) -> List[BriefInvalidation]:
    """
    Deduces invalidation thresholds and rules for BUY or SELL setups.
    All strings are formatted in Thai.
    """
    conditions = []
    direction = data.get("direction", "NEUTRAL").upper()
    sl = data.get("sl", 0.0)
    
    # 1. SL breach check
    if sl > 0:
        if "BUY" in direction:
            conditions.append(BriefInvalidation(
                condition="จุดตัดขาดทุนถูกทำลาย (Stop Loss Breach)",
                price_level=sl,
                notes=f"หากราคาแท่งเทียนปิดตัวต่ำกว่าระดับจุดตัดขาดทุน (SL) ที่ {sl:.4f} สัญญาณซื้อจะสูญเสียผลทันที"
            ))
        elif "SELL" in direction:
            conditions.append(BriefInvalidation(
                condition="จุดตัดขาดทุนถูกทำลาย (Stop Loss Breach)",
                price_level=sl,
                notes=f"หากราคาแท่งเทียนปิดตัวสูงกว่าระดับจุดตัดขาดทุน (SL) ที่ {sl:.4f} สัญญาณขายจะสูญเสียผลทันที"
            ))
            
    # 2. Support / Resistance level breach
    support = data.get("support_level", data.get("entry", 0.0) * 0.95)
    resistance = data.get("resistance_level", data.get("entry", 0.0) * 1.05)
    
    if "BUY" in direction and support > 0 and support != sl:
        conditions.append(BriefInvalidation(
            condition="แนวรับสวิงหลุด (Swing Support Failure)",
            price_level=support,
            notes=f"หากราคาหลุดทำลายระดับแนวรับตามสวิงล่าสุดที่ {support:.4f}"
        ))
    elif "SELL" in direction and resistance > 0 and resistance != sl:
        conditions.append(BriefInvalidation(
            condition="แนวต้านสวิงถูกทะลุ (Swing Resistance Failure)",
            price_level=resistance,
            notes=f"หากราคาทะลุทำลายระดับแนวต้านตามสวิงล่าสุดที่ {resistance:.4f}"
        ))
        
    # 3. Market Regime changes
    conditions.append(BriefInvalidation(
        condition="การเปลี่ยนสภาวะตลาด (Market Regime Shift)",
        price_level=0.0,
        notes="หากระบบตรวจพบว่าสภาวะตลาดเปลี่ยนทิศทางเป็นตลาดไซด์เวย์ (SIDEWAYS) หรือสภาพคล่องต่ำ (LOW_LIQUIDITY) สัญญาณจะถูกยกเลิก"
    ))
    
    # 4. Risk / Veto check
    if data.get("portfolio_risk_status", "OK") == "BLOCKED":
        conditions.append(BriefInvalidation(
            condition="บล็อกความเสี่ยงพอร์ต (Portfolio Risk Block)",
            price_level=0.0,
            notes="ปริมาณความเสี่ยงเปิดสุทธิ หรือจำนวนการขาดทุนสะสมรายวันเต็มขีดจำกัดสูงสุด"
        ))
        
    return conditions
