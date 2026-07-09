import datetime
import logging
import json
from typing import Dict, Any, Optional
from tradenexus.explain.brief_models import DecisionBrief, BriefRiskPlan, BriefPortfolioCheck
from tradenexus.explain.reason_builder import build_reasons
from tradenexus.explain.invalidation import generate_invalidation_conditions
from tradenexus.explain.warning_summarizer import summarize_warnings
from tradenexus.portfolio.position_sizing import calculate_position_size
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings, load_symbol_profile
from tradenexus.portfolio.exposure import calculate_portfolio_exposure
from tradenexus.portfolio.correlation import calculate_returns_correlation
from tradenexus.portfolio.limits import check_portfolio_risk_limits

logger = logging.getLogger(__name__)

def generate_decision_brief(
    data: Dict[str, Any],
    db_path: str = None
) -> DecisionBrief:
    """
    Orchestrator that loads context data and builds a populated DecisionBrief.
    """
    symbol = data.get("symbol", "UNKNOWN")
    tf = data.get("timeframe", "1h")
    state = data.get("decision_state", "NO TRADE")
    direction = data.get("direction", "NEUTRAL")
    alignment = data.get("alignment_type", "CONFLICTED")
    conf_score = data.get("confluence_score", 0.0)
    regime = data.get("primary_regime", "UNKNOWN")
    
    # Flags parsing
    flags_raw = data.get("regime_flags", [])
    if isinstance(flags_raw, str):
        flags = flags_raw.split(",") if flags_raw else []
    else:
        flags = list(flags_raw)
        
    # 1. Load Portfolio settings and check limits if database is accessible
    p_settings = load_portfolio_settings(db_path)
    p_profile = load_symbol_profile(symbol, db_path)
    
    p_status = data.get("portfolio_risk_status", "OK")
    p_reasons = data.get("portfolio_reasons", [])
    p_warns = data.get("portfolio_warnings", [])
    
    # Position sizing variables
    pv = p_profile.point_value if p_profile else p_settings.default_point_value
    mult = p_profile.contract_multiplier if p_profile else p_settings.default_contract_multiplier
    min_size = p_profile.min_position_size if p_profile else 0.01
    step = p_profile.position_step if p_profile else 0.01
    
    entry = data.get("entry", 0.0)
    sl = data.get("sl", 0.0)
    tp1 = data.get("tp1", 0.0)
    tp2 = data.get("tp2", 0.0)
    rr = data.get("rr_tp1", 0.0)
    
    size_units = 0.0
    risk_dollars = 0.0
    
    if entry > 0 and sl > 0 and direction != "NEUTRAL":
        sizing_res = calculate_position_size(
            account_equity=p_settings.account_equity,
            risk_per_trade_pct=p_settings.risk_per_trade_pct,
            entry=entry,
            stop_loss=sl,
            direction=direction,
            point_value=pv,
            contract_multiplier=mult,
            min_position_size=min_size,
            position_step=step,
            tp1=tp1,
            tp2=tp2
        )
        size_units = sizing_res.position_size_units
        risk_dollars = sizing_res.risk_amount
        
    risk_plan = BriefRiskPlan(
        entry=entry,
        sl=sl,
        tp1=tp1,
        tp2=tp2,
        rr_tp1=rr,
        position_size=size_units,
        risk_amount=risk_dollars
    )
    
    # Re-verify portfolio limit blocker if needed and not already provided
    if not data.get("portfolio_risk_status") and db_path:
        exposure = calculate_portfolio_exposure(db_path, p_settings)
        # To avoid slow downloads, use cached watchlist correlation inside scan run or simple empty correlation
        from tradenexus.portfolio.risk_models import CorrelationRiskResult
        corr = CorrelationRiskResult({}, [], [], "")
        limits_res = check_portfolio_risk_limits(p_settings, exposure, corr, direction)
        p_status = limits_res.risk_status
        p_reasons = limits_res.reasons
        p_warns = limits_res.warnings
        
    portfolio_check = BriefPortfolioCheck(
        portfolio_risk_status=p_status,
        reasons=p_reasons,
        warnings=p_warns
    )
    
    # 2. Build explanation sub-fields
    data_for_reasons = dict(data)
    data_for_reasons["portfolio_risk_status"] = p_status
    
    reasons = build_reasons(data_for_reasons)
    
    # Warnings processing
    raw_warnings = list(data.get("warnings", []))
    if isinstance(raw_warnings, str):
        raw_warnings = json.loads(raw_warnings) if raw_warnings else []
        
    # Append portfolio warnings
    raw_warnings.extend(p_warns)
    if p_status == "BLOCKED":
        raw_warnings.extend(p_reasons)
        
    warnings = summarize_warnings(raw_warnings)
    invalidation = generate_invalidation_conditions(data_for_reasons)
    
    # Headline & summary
    dir_th = "ซื้อ (BUY)" if direction == "BUY" else ("ขาย (SELL)" if direction == "SELL" else "เป็นกลาง (NEUTRAL)")
    headline = f"เกิดสัญญาณเทรดฝั่ง {dir_th} สำหรับ {symbol}"
    summary = f"ยืนยันแนวโน้มฝั่ง {dir_th} ในกรอบเวลา {tf} ด้วยความสอดคล้อง (Confluence) {conf_score:.0f}%"
    
    # Next Action
    next_action = "เฝ้าระวังและรอการยืนยันสัญญาณเพิ่มเติม"
    alert_status = data.get("alert_status", "")
    if alert_status == "BLOCKED_BY_PLAYBOOK":
        next_action = "ระงับการเข้าเทรด (PLAYBOOK BLOCKED): ห้ามเข้าเทรดเนื่องจากละเมิดกฎวินัยหรือขีดจำกัดความเสี่ยงของ Playbook"
    elif state == "ENTRY TRIGGERED":
        if p_status == "BLOCKED":
            next_action = "ระงับออเดอร์ (ALERT BLOCKED): ห้ามเทรดเนื่องจากความเสี่ยงพอร์ตโดยรวมเกินขีดจำกัดสูงสุด"
        else:
            next_action = "เปิดออเดอร์ (EXECUTE): สามารถเข้าซื้อขายและตั้งค่าจำกัดความเสี่ยง (Stop Loss) ทันที"
    elif state == "READY":
        next_action = "เตรียมออเดอร์ (PREPARE): รอเปิดคำสั่งซื้อขายล่วงหน้า (Pending Order) เมื่อราคาถึงจุดเข้าเทรด"
        
    return DecisionBrief(
        symbol=symbol,
        timeframe=tf,
        decision_state=state,
        direction=direction,
        alignment_type=alignment,
        confluence_score=conf_score,
        primary_regime=regime,
        regime_flags=flags,
        risk_plan=risk_plan,
        portfolio_check=portfolio_check,
        invalidation_conditions=invalidation,
        headline=headline,
        summary=summary,
        reasons=reasons,
        warnings=warnings,
        next_action=next_action,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
