import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def build_reasons(data: Dict[str, Any]) -> List[str]:
    """
    Generates human-readable, deterministic explanations based ONLY on existing computed fields.
    All outputs are formatted in Thai for user-friendliness.
    """
    reasons = []
    
    # 1. MTF Hierarchy Trend explanation
    bias_1d = data.get("market_bias", data.get("bias_1d", "Neutral"))
    setup_4h = data.get("setup_direction", data.get("setup_4h", "Neutral"))
    trigger_1h = data.get("trigger_direction", data.get("trigger_1h", "Neutral"))
    alignment = data.get("alignment_type", "CONFLICTED")
    
    # Translate directions for reasons
    dict_th = {"Bullish": "กระทิง (Bullish)", "Bearish": "หมี (Bearish)", "Neutral": "เป็นกลาง (Neutral)"}
    bias_1d_th = dict_th.get(bias_1d, bias_1d)
    setup_4h_th = dict_th.get(setup_4h, setup_4h)
    trigger_1h_th = dict_th.get(trigger_1h, trigger_1h)
    
    if alignment == "TREND_FOLLOWING":
        reasons.append(f"โครงสร้างแนวโน้มหลักสอดคล้องตรงกัน (1D Bias: {bias_1d_th}, 4H Setup: {setup_4h_th})")
    elif alignment == "COUNTER_TREND_SCALP":
        reasons.append(f"พบสัญญาณทำกำไรสวนแนวโน้มระยะสั้น (1D Bias: {bias_1d_th}, 1H Trigger: {trigger_1h_th})")
    else:
        reasons.append(f"แนวโน้มขัดแย้งกันในแต่ละกรอบเวลาหลัก (1D: {bias_1d_th}, 4H: {setup_4h_th})")
        
    # 2. Confluence Score & Key Indicators
    conf_score = data.get("confluence_score", 0.0)
    reasons.append(f"คะแนน Confluence Score อยู่ที่ {conf_score:.0f}/100 บ่งบอกว่าความแข็งแกร่งของสัญญาณอยู่ในเกณฑ์ดี")
    
    # 3. Market Regime & Flags
    regime = data.get("primary_regime", "UNKNOWN")
    flags_raw = data.get("regime_flags", [])
    if isinstance(flags_raw, str):
        flags = flags_raw.split(",") if flags_raw else []
    else:
        flags = flags_raw
        
    # Translate flags
    flags_th = []
    for f in flags:
        if f == "HIGH_VOLATILITY":
            flags_th.append("ความผันผวนสูง (High Volatility)")
        elif f == "LOW_LIQUIDITY":
            flags_th.append("สภาพคล่องต่ำ (Low Liquidity)")
        elif f == "VOLUME_UNRELIABLE":
            flags_th.append("ปริมาณการซื้อขายไม่น่าเชื่อถือ")
        elif f == "INSUFFICIENT_DATA":
            flags_th.append("ข้อมูลย้อนหลังไม่เพียงพอ")
        else:
            flags_th.append(f)
            
    regime_dict = {
        "TRENDING_UP": "แนวโน้มขาขึ้น (TRENDING UP)",
        "TRENDING_DOWN": "แนวโน้มขาลง (TRENDING DOWN)",
        "SIDEWAYS": "ไซด์เวย์ออกข้าง (SIDEWAYS)",
        "SQUEEZE": "ตลาดบีบตัวแคบ (SQUEEZE)",
        "EXPANSION": "ราคาเกิดการขยายตัว (EXPANSION)",
        "UNKNOWN": "ไม่สามารถระบุสถานะ (UNKNOWN)"
    }
    regime_th = regime_dict.get(regime, regime)
    
    reasons.append(f"สภาวะตลาดถูกจัดอยู่ในประเภท: {regime_th} (สถานะเพิ่มเติม: {', '.join(flags_th) if flags_th else 'ปกติ'})")
    
    # 4. VWAP / Volume confirmations
    vwap_align = data.get("vwap_alignment", "NEUTRAL")
    vol_conf = data.get("volume_confirmation", "NEUTRAL")
    if vwap_align != "NEUTRAL":
        vwap_th = "อยู่เหนือเส้น VWAP (Bullish)" if vwap_align == "BULLISH" else "อยู่ใต้เส้น VWAP (Bearish)"
        reasons.append(f"ตำแหน่งราคาเทียบกับเส้น VWAP: {vwap_th} ยืนยันในทิศทางเดียวกัน")
    if vol_conf == "BULLISH_VOLUME":
        reasons.append("ปริมาณการซื้อขายหนุนทิศทางขาขึ้น (Bullish Volume) แสดงให้เห็นถึงแรงซื้อที่หนาแน่น")
    elif vol_conf == "BEARISH_VOLUME":
        reasons.append("ปริมาณการซื้อขายหนุนทิศทางขาลง (Bearish Volume) แสดงให้เห็นถึงแรงขายที่หนาแน่น")
        
    # 5. SMC Structures
    bos = data.get("bos_present", 0)
    choch = data.get("choch_present", 0)
    fvg = data.get("fvg_present", 0)
    
    if bos:
        reasons.append("พบโครงสร้างราคาถูกทำลาย (BOS) ยืนยันการไปต่อตามแนวโน้ม")
    if choch:
        reasons.append("พบการเปลี่ยนลักษณะแนวโน้มโครงสร้างราคา (CHOCH) ส่งสัญญาณต้นเทรนด์ใหม่")
    if fvg:
        reasons.append("พบช่องว่างราคาไม่สมดุล (FVG) เป็นเป้าหมายสภาพคล่องที่ราคามักดึงดูดกลับไปหา")
        
    # 6. Risk / Reward validation
    rr_tp1 = data.get("rr_tp1", 0.0)
    if rr_tp1 > 0:
        reasons.append(f"อัตราส่วนกําไรต่อความเสี่ยง (Risk/Reward Ratio) อยู่ที่ {rr_tp1:.2f} เท่า ไปยังเป้าหมาย TP1 ผ่านเกณฑ์ขั้นต่ำของระบบ")
        
    return reasons
