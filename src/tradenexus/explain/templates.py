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
    warnings_str = ", ".join(brief.warnings[:2]) if brief.warnings else "None"
    
    lines = [
        f"Asset: {brief.symbol} ({brief.timeframe}) | State: {brief.decision_state}",
        f"Direction: {brief.direction} | Setup: {brief.alignment_type} | Confluence: {brief.confluence_score:.0f}/100",
        f"Why: {brief.summary}",
        f"Risk: Entry {entry:.2f}, SL {sl:.2f}, TP1 {tp1:.2f}, RR {rr:.2f}R. Size: {size:.2f} units.",
        f"Portfolio: {p_status} | Warnings: {warnings_str}"
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
    p_reasons = ", ".join(pc.reasons) if pc and pc.reasons else "None"
    p_warns = ", ".join(pc.warnings) if pc and pc.warnings else "None"
    
    invals = "\n".join([f"- {c.condition}: {c.notes}" for c in brief.invalidation_conditions]) if brief.invalidation_conditions else "- None"
    reasons = "\n".join([f"- {r}" for r in brief.reasons]) if brief.reasons else "- None"
    warnings = "\n".join([f"- {w}" for w in brief.warnings]) if brief.warnings else "- None"
    
    text = f"""### TradeNexus Decision Brief: {brief.symbol} ({brief.timeframe})
**Headline**: {brief.headline}
**Decision State**: {brief.decision_state} ({brief.direction})
**Market Regime**: {brief.primary_regime}

#### 💡 Technical Thesis:
{reasons}

#### 🛡️ Risk Plan:
- Entry: {entry:.4f}
- Stop Loss: {sl:.4f}
- Take Profit 1: {tp1:.4f} (RR: {rr:.2f}R)
- Take Profit 2: {tp2:.4f}
- Sized Allocation: {size:.4f} units

#### 💼 Portfolio Check:
- Risk Status: **{p_status}**
- Block Reasons: {p_reasons}
- Warnings: {p_warns}

#### ⚠️ Warnings:
{warnings}

#### ❌ Invalidation triggers:
{invals}

#### 🚀 Next Action:
{brief.next_action}
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
        f"🚨 **TradeNexus Alert: {brief.symbol} ({brief.timeframe})**\n"
        f"**Decision**: {brief.decision_state} ({brief.direction})\n"
        f"**Confluence**: {brief.confluence_score:.0f}/100 | Regime: {brief.primary_regime}\n"
        f"**Risk Plan**: Entry {entry:.2f} | SL {sl:.2f} | TP1 {tp1:.2f} ({rr:.2f}R) | Size: {size:.2f} units\n"
        f"**Portfolio Risk**: {p_status}\n"
        f"**Action**: {brief.next_action}"
    )
    return text

def format_journal_brief(brief: DecisionBrief) -> str:
    return format_compact_brief(brief)

def format_scan_card_brief(brief: DecisionBrief) -> str:
    return f"Confluence: {brief.confluence_score:.0f}%, RR: {brief.risk_plan.rr_tp1 if brief.risk_plan else 0.0:.2f}R | {brief.summary}"
