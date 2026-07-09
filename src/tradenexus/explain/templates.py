import logging
from tradenexus.explain.brief_models import DecisionBrief

logger = logging.getLogger(__name__)

def format_compact_brief(brief: DecisionBrief) -> str:
    rp = brief.risk_plan
    pc = brief.portfolio_check
    
    entry = rp.entry if rp else 0.0
    sl = rp.sl if rp else 0.0
    tp1 = rp.tp1 if rp else 0.0
    rr = rp.rr_tp1 if rp else 0.0
    size = rp.position_size if rp else 0.0
    
    p_status = pc.portfolio_risk_status if pc else "OK"
    warnings_str = ", ".join(brief.warnings[:2]) if brief.warnings else "ไม่มีคำเตือน"
    
    lines = [
        f"สินทรัพย์: {brief.symbol} ({brief.timeframe}) | สถานะ: {brief.decision_state}",
        f"ทิศทาง: {brief.direction} | รูปแบบ: {brief.alignment_type} | ความสอดคล้อง (Confluence): {brief.confluence_score:.0f}/100",
        f"เหตุผลหลัก: {brief.summary}",
        f"การควบคุมความเสี่ยง: เข้าที่ {entry:.2f}, ตัดขาดทุน {sl:.2f}, เป้ากำไรแรก {tp1:.2f}, อัตรา RR {rr:.2f}R. ขนาดไม้: {size:.2f} หน่วย.",
        f"ความเสี่ยงพอร์ต: {p_status} | คำเตือนสำคัญ: {warnings_str}"
    ]
    return "\n".join(lines)

def format_full_brief(brief: DecisionBrief) -> str:
    rp = brief.risk_plan
    pc = brief.portfolio_check
    
    entry = rp.entry if rp else 0.0
    sl = rp.sl if rp else 0.0
    tp1 = rp.tp1 if rp else 0.0
    tp2 = rp.tp2 if rp else 0.0
    rr = rp.rr_tp1 if rp else 0.0
    size = rp.position_size if rp else 0.0
    
    p_status = pc.portfolio_risk_status if pc else "OK"
    p_reasons = ", ".join(pc.reasons) if pc and pc.reasons else "ไม่มี"
    p_warns = ", ".join(pc.warnings) if pc and pc.warnings else "ไม่มี"
    
    invals = "\n".join([f"- **{c.condition}**: {c.notes}" for c in brief.invalidation_conditions]) if brief.invalidation_conditions else "- ไม่มี"
    reasons = "\n".join([f"- {r}" for r in brief.reasons]) if brief.reasons else "- ไม่มี"
    warnings = "\n".join([f"- {w}" for w in brief.warnings]) if brief.warnings else "- ไม่มี"
    
    text = f"""### 📖 สรุปผลสรุปการวิเคราะห์ (TradeNexus Decision Brief): {brief.symbol} ({brief.timeframe})
- **หัวข้อหลัก (Headline)**: {brief.headline}
- **สถานะปัจจุบัน (Decision State)**: {brief.decision_state} ({brief.direction})
- **สภาวะตลาด (Market Regime)**: {brief.primary_regime}

#### 💡 บทวิเคราะห์ทางเทคนิค (Technical Thesis):
{reasons}

#### 🛡️ แผนการบริหารความเสี่ยง (Risk Plan):
- **จุดเข้าเทรด (Entry Zone)**: {entry:.4f}
- **จุดตัดขาดทุน (Stop Loss)**: {sl:.4f}
- **จุดทำกำไร 1 (Take Profit 1)**: {tp1:.4f} (อัตรา RR: {rr:.2f}R)
- **จุดทำกำไร 2 (Take Profit 2)**: {tp2:.4f}
- **ขนาดออเดอร์ที่แนะนำ (Position Size)**: {size:.4f} หน่วย

#### 💼 ตรวจสอบความเสี่ยงพอร์ต (Portfolio Check):
- สถานะความเสี่ยงพอร์ตโดยรวม: **{p_status}**
- เหตุผลการบล็อกส่งคำสั่ง: {p_reasons}
- ข้อควรระวังของพอร์ต: {p_warns}

#### ⚠️ คำเตือน / ข้อควรระวัง (Warnings):
{warnings}

#### ❌ เงื่อนไขยกเลิกสัญญาณ (Invalidation Triggers):
{invals}

#### 🚀 การดำเนินการขั้นถัดไป (Next Action):
- **{brief.next_action}**
"""
    return text

def format_alert_brief(brief: DecisionBrief) -> str:
    rp = brief.risk_plan
    pc = brief.portfolio_check
    
    entry = rp.entry if rp else 0.0
    sl = rp.sl if rp else 0.0
    tp1 = rp.tp1 if rp else 0.0
    rr = rp.rr_tp1 if rp else 0.0
    size = rp.position_size if rp else 0.0
    p_status = pc.portfolio_risk_status if pc else "OK"
    
    text = (
        f"🚨 **แจ้งเตือน TradeNexus: {brief.symbol} ({brief.timeframe})**\n"
        f"**การตัดสินใจ**: {brief.decision_state} ({brief.direction})\n"
        f"**Confluence**: {brief.confluence_score:.0f}/100 | สภาวะตลาด: {brief.primary_regime}\n"
        f"**แผนความเสี่ยง**: เข้าซื้อ {entry:.2f} | SL {sl:.2f} | TP1 {tp1:.2f} ({rr:.2f}R) | ขนาด: {size:.2f} หน่วย\n"
        f"**ความเสี่ยงพอร์ต**: {p_status}\n"
        f"**การดำเนินการ**: {brief.next_action}"
    )
    return text

def format_journal_brief(brief: DecisionBrief) -> str:
    return format_compact_brief(brief)

def format_scan_card_brief(brief: DecisionBrief) -> str:
    return f"Confluence: {brief.confluence_score:.0f}%, RR: {brief.risk_plan.rr_tp1 if brief.risk_plan else 0.0:.2f}R | {brief.summary}"
