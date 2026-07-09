import logging

logger = logging.getLogger(__name__)

def calculate_confluence_score(latest_data: dict) -> dict:
    """
    Confluence Score 2.0.
    
    Computes directional alignment and setup quality based on indicators,
    market regime, volume flows, and risk parameters.
    
    All reasons and warnings are formatted in Thai for user-friendliness.
    """
    reasons = []
    warnings = []
    
    # 1. Directional Score Calculation (-100 to +100)
    dir_score = 0.0
    
    cdc_trend = latest_data.get("CDC_Trend", "Neutral")
    supertrend_dir = latest_data.get("SuperTrend_Direction", "Neutral")
    macd_trend = latest_data.get("MACD_Trend", "Neutral")
    kama_trend = latest_data.get("Adaptive_Trend", "Neutral")
    
    if cdc_trend == "Bullish":
        dir_score += 40.0
        reasons.append("CDC ActionZone เป็นสัญญาณซื้อ Bullish (+40)")
    elif cdc_trend == "Bearish":
        dir_score -= 40.0
        reasons.append("CDC ActionZone เป็นสัญญาณขาย Bearish (-40)")
        
    if supertrend_dir == "Bullish":
        dir_score += 40.0
        reasons.append("SuperTrend เป็นแนวโน้มขาขึ้น Bullish (+40)")
    elif supertrend_dir == "Bearish":
        dir_score -= 40.0
        reasons.append("SuperTrend เป็นแนวโน้มขาลง Bearish (-40)")
        
    if macd_trend == "Bullish":
        dir_score += 10.0
        reasons.append("MACD ทิศทางขาขึ้น Bullish (+10)")
    elif macd_trend == "Bearish":
        dir_score -= 10.0
        reasons.append("MACD ทิศทางขาลง Bearish (-10)")
        
    if kama_trend == "Bullish":
        dir_score += 10.0
        reasons.append("KAMA/Adaptive Trend ขาขึ้น Bullish (+10)")
    elif kama_trend == "Bearish":
        dir_score -= 10.0
        reasons.append("KAMA/Adaptive Trend ขาลง Bearish (-10)")
        
    is_bullish = dir_score > 0
    
    # 2. Quality Score 2.0 (0 to 100)
    q_score = 0.0
    
    # A. Trend agreement (max 25 points)
    if cdc_trend == supertrend_dir and cdc_trend != "Neutral":
        q_score += 25.0
        reasons.append("แนวโน้มหลัก (1D) และแนวโน้มรอง (4H) สอดคล้องเต็มรูปแบบ (+25)")
    elif cdc_trend != "Neutral" or supertrend_dir != "Neutral":
        q_score += 12.5
        reasons.append("แนวโน้มสอดคล้องบางส่วน (+12.5)")
        
    # B. Momentum strength (max 15 points)
    adx = latest_data.get("ADX", 20.0)
    if adx >= 25:
        q_score += 15.0
        reasons.append(f"แนวโน้มมีกำลังสูงมาก ADX ({adx:.1f} >= 25) (+15)")
    elif adx < 20:
        q_score += 5.0
        warnings.append(f"แนวโน้มไม่มีกำลัง ADX อ่อนแรง ({adx:.1f} < 20) (-10)")
    else:
        q_score += 10.0
        
    # C. SMC structure (max 20 points)
    support_src = latest_data.get("Support_Source", "FALLBACK")
    resistance_src = latest_data.get("Resistance_Source", "FALLBACK")
    relevant_src = support_src if is_bullish else resistance_src
    
    if relevant_src == "CONFIRMED_SWING":
        q_score += 15.0
        reasons.append("ใช้ระดับแนวรับ/แนวต้าน Swing ระดับที่คอนเฟิร์มแล้ว (+15)")
    else:
        q_score += 5.0
        warnings.append("ใช้ระดับแนวรับ/แนวต้านสำรอง (Fallback S/R) (-10)")
        
    # Check for active structures (BOS, CHOCH, FVG)
    bos = latest_data.get("BOS_Present", 0)
    choch = latest_data.get("CHOCH_Present", 0)
    fvg = latest_data.get("FVG_Present", 0)
    
    if bos or choch or fvg:
        q_score += 5.0
        reasons.append("มีโครงสร้างราคาเบรกเอาต์สนับสนุน / FVG ทำงาน (+5)")
        
    # D. Market Regime (max 15 points)
    regime = latest_data.get("primary_regime", "UNKNOWN")
    regime_score = latest_data.get("regime_score", 50.0)
    regime_flags = latest_data.get("regime_flags", "")
    
    regime_dict = {
        "TRENDING_UP": "แนวโน้มขาขึ้น (TRENDING UP)",
        "TRENDING_DOWN": "แนวโน้มขาลง (TRENDING DOWN)",
        "SIDEWAYS": "ออกข้างไซด์เวย์ (SIDEWAYS)",
        "SQUEEZE": "ตลาดบีบตัวแคบ (SQUEEZE)",
        "EXPANSION": "ราคาขยายตัวรวดเร็ว (EXPANSION)",
        "UNKNOWN": "ไม่สามารถระบุสถานะ (UNKNOWN)"
    }
    regime_desc = regime_dict.get(regime, regime)
    
    if regime in ["TRENDING_UP", "TRENDING_DOWN", "EXPANSION"]:
        q_score += 15.0
        reasons.append(f"สภาวะตลาดเกื้อหนุนกลยุทธ์ปัจจุบัน ({regime_desc}) (+15)")
    elif regime in ["SIDEWAYS", "SQUEEZE"]:
        q_score += 5.0
        warnings.append(f"ตลาดออกข้าง/บีบตัว ({regime_desc}) - คุณภาพจุดเข้าลดลง (-10)")
    else:
        q_score += 10.0
        
    if "HIGH_VOLATILITY" in regime_flags:
        q_score -= 5.0
        warnings.append("ความผันผวนสูงมาก - เพิ่มความเสี่ยงจุดตัดขาดทุน (-5)")
    if "LOW_LIQUIDITY" in regime_flags:
        q_score -= 10.0
        warnings.append("สภาพคล่องต่ำ - เพิ่มความเสี่ยงในการคลาดเคลื่อนของราคา (Slippage) (-10)")
        
    # E. Volume / VWAP Confirmation (max 10 points)
    has_vol_warning = (latest_data.get("Volume_Warning", "") != "")
    vol_conf = latest_data.get("Volume_Confirmation", "NEUTRAL")
    
    vwap = latest_data.get("VWAP", latest_data.get("Close"))
    price = latest_data.get("Close")
    
    vwap_bull = price > vwap
    vwap_bear = price < vwap
    
    if has_vol_warning:
        q_score += 5.0  # Neutral contribution
        warnings.append("ตัวชี้วัดวอลลุ่มแสดงสถานะเป็นกลาง (ข้อมูลไม่พร้อมใช้งาน/ไม่เสถียร)")
    else:
        # VWAP alignment (5 points)
        if (is_bullish and vwap_bull) or (not is_bullish and vwap_bear):
            q_score += 5.0
            reasons.append("ราคาอยู่ในตำแหน่งสอดคล้องกับแนวโน้มของ VWAP (+5)")
            
        # Volume Flow Confirmation (5 points)
        if (is_bullish and vol_conf == "BULLISH") or (not is_bullish and vol_conf == "BEARISH"):
            q_score += 5.0
            reasons.append("ทิศทางของวอลลุ่มช่วยยืนยันการเบรกเอาต์ (+5)")
        else:
            q_score += 2.0
            
    # F. Risk/Reward quality (max 15 points)
    rr_tp1 = latest_data.get("RR_TP1", 0.0)
    if rr_tp1 >= 1.5:
        q_score += 15.0
        reasons.append(f"อัตราผลตอบแทนต่อความเสี่ยงสูงดีเยี่ยม ({rr_tp1:.2f} >= 1.5) (+15)")
    else:
        q_score += 0.0
        warnings.append(f"อัตราผลตอบแทนต่อความเสี่ยงต่ำกว่าเกณฑ์ขั้นต่ำ ({rr_tp1:.2f} < 1.5)")
        
    # 3. Combine into Confluence Score (0 to 100)
    conf_score = (abs(dir_score) * 0.5) + (q_score * 0.5)
    
    # Safe bounds
    dir_score = max(min(dir_score, 100.0), -100.0)
    q_score = max(min(q_score, 100.0), 0.0)
    conf_score = max(min(conf_score, 100.0), 0.0)
    
    return {
        "directional_score": dir_score,
        "quality_score": q_score,
        "confluence_score": conf_score,
        "reasons": reasons,
        "warnings": warnings
    }
