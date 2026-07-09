import json
import datetime
from typing import List, Dict, Any
from tradenexus.reports.compliance_models import ComplianceMetrics, ComplianceReport
from tradenexus.reports.compliance_repository import load_compliance_data, get_workspace_name
from tradenexus.reports.performance_summary import calculate_performance_metrics
from tradenexus.playbook.playbook_repository import get_active_playbook
from tradenexus.presets.preset_repository import load_preset
from tradenexus.portfolio.portfolio_repository import load_portfolio_settings

def calculate_compliance_score(metrics: ComplianceMetrics) -> float:
    """
    Computes a deterministic compliance score between 0 and 100.
    Formula:
      - Start at 100.0
      - Deduct up to 25.0 points for Playbook violations (5.0 points per violation)
      - Deduct up to 25.0 points for Portfolio risk blocks (10.0 points per block)
      - Deduct up to 15.0 points for invalid data (scaled by rate of invalid signals)
      - Deduct up to 15.0 points for low RR ratio violations (scaled by rate of low RR signals)
      - Deduct up to 10.0 points for low confluence violations (scaled by rate of low confluence signals)
      - Deduct up to 10.0 points for discipline violations (session, cooldown, overtrading, 5.0 points each)
    """
    if metrics.total_signals == 0:
        return 100.0
        
    score = 100.0
    
    # 1. Playbook Violation Penalty (up to -25 points)
    score -= min(25.0, metrics.playbook_violation_count * 5.0)
    
    # 2. Portfolio Risk Blocks Penalty (up to -25 points)
    score -= min(25.0, metrics.alerts_blocked_portfolio * 10.0)
    
    # 3. Data Quality Penalty (up to -15 points)
    invalid_pct = metrics.signals_invalid_data / metrics.total_signals
    score -= invalid_pct * 15.0
    
    # 4. RR Compliance Penalty (up to -15 points)
    low_rr_pct = metrics.low_rr_violations / metrics.total_signals
    score -= low_rr_pct * 15.0
    
    # 5. Confluence Compliance Penalty (up to -10 points)
    low_conf_pct = metrics.low_confluence_violations / metrics.total_signals
    score -= low_conf_pct * 10.0
    
    # 6. Discipline Penalty (session, cooldown, overtrading) (up to -10 points)
    discipline_violations = metrics.session_violations + metrics.cooldown_violations + metrics.overtrading_warnings
    score -= min(10.0, discipline_violations * 5.0)
    
    return float(max(0.0, min(100.0, score)))

def generate_compliance_report(
    workspace_id: str,
    start_date: str,
    end_date: str,
    db_path: str = None
) -> ComplianceReport:
    """
    Retrieves records for the active workspace, runs compliance checks,
    computes performance metrics, and generates a ComplianceReport.
    """
    raw_data = load_compliance_data(workspace_id, start_date, end_date, db_path)
    
    signals = raw_data["signals"]
    alert_logs = raw_data["alert_logs"]
    trades = raw_data["trades"]
    playbook_events = raw_data["playbook_events"]
    risk_events = raw_data["risk_events"]
    recommendations = raw_data["recommendations"]
    
    metrics = ComplianceMetrics()
    
    # 1. Signals Metrics
    metrics.total_signals = len(signals)
    if metrics.total_signals > 0:
        total_rr = 0.0
        total_conf = 0.0
        
        for sig in signals:
            if sig.get("is_actionable") == 1:
                metrics.actionable_signals += 1
                
            total_rr += sig.get("rr_tp1") or 0.0
            total_conf += sig.get("confluence_score") or 0.0
            
            # Data quality checks
            if sig.get("data_quality_valid") == 0:
                metrics.signals_invalid_data += 1
                
            dq_warn_str = sig.get("data_quality_warnings_json")
            if dq_warn_str:
                try:
                    dq_warns = json.loads(dq_warn_str)
                    if isinstance(dq_warns, list) and len(dq_warns) > 0:
                        metrics.signals_data_warnings += 1
                except Exception:
                    pass
                    
        metrics.average_rr = total_rr / metrics.total_signals
        metrics.average_confluence = total_conf / metrics.total_signals
        
    # 2. Alert Log Metrics
    metrics.alerts_sent = len([al for al in alert_logs if al.get("status") == "SENT"])
    
    # 3. Portfolio risk blocks
    metrics.alerts_blocked_portfolio = len([re for re in risk_events if re.get("risk_status") == "BLOCKED"])
    
    # 4. Playbook violation metrics
    # Note: playbook violations are logged in playbook_rule_events when evaluated in rule_engine.
    # Total violations count
    violations = [pe for pe in playbook_events if pe.get("event_type") == "VIOLATION"]
    metrics.playbook_violation_count = len(violations)
    
    for v in violations:
        details_str = v.get("details_json") or "{}"
        try:
            details = json.loads(details_str)
            msg = str(details.get("message", "")).lower()
        except Exception:
            msg = ""
            
        if "cooldown" in msg:
            metrics.cooldown_violations += 1
        elif "session" in msg:
            metrics.session_violations += 1
        elif "confluence" in msg:
            metrics.low_confluence_violations += 1
        elif "rr" in msg or "ratio" in msg or "risk-to-reward" in msg:
            metrics.low_rr_violations += 1
        elif "limit" in msg or "max trades" in msg or "overtrading" in msg:
            metrics.overtrading_warnings += 1
            
    # Calculate playbook blocks from alerts that might have been rejected
    metrics.alerts_blocked_playbook = metrics.playbook_violation_count
    
    # 5. Performance Metrics
    perf = calculate_performance_metrics(trades)
    metrics.trades_opened = perf["trades_opened"]
    metrics.trades_closed = perf["trades_closed"]
    metrics.win_rate = perf["win_rate"]
    metrics.expectancy = perf["expectancy"]
    metrics.profit_factor = perf["profit_factor"]
    metrics.max_drawdown = perf["max_drawdown"]
    
    # 6. Compliance score
    score = calculate_compliance_score(metrics)
    
    ws_name = get_workspace_name(workspace_id, db_path)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 7. Preset Drift Calculation
    active_preset_id = None
    active_preset_name = None
    preset_drift_detected = False
    preset_drift_fields = []
    
    playbook = get_active_playbook(db_path, workspace_id)
    if playbook and playbook.active_preset_id:
        active_preset_id = playbook.active_preset_id
        preset = load_preset(active_preset_id, workspace_id, db_path)
        if preset:
            active_preset_name = preset.name
            portfolio = load_portfolio_settings(db_path, workspace_id)
            
            # Fields comparison
            playbook_checks = [
                ("min_confluence_score", playbook.min_confluence_score, preset.min_confluence_score),
                ("min_rr", playbook.min_rr, preset.min_rr),
                ("max_trades_per_day", playbook.max_trades_per_day, preset.max_trades_per_day),
                ("max_losses_per_day", playbook.max_losses_per_day, preset.max_losses_per_day),
                ("max_consecutive_losses", playbook.max_consecutive_losses, preset.max_consecutive_losses),
                ("cooldown_minutes_after_loss", playbook.cooldown_minutes_after_loss, preset.cooldown_minutes_after_loss),
                ("allowed_symbols", playbook.allowed_symbols, preset.allowed_symbols),
                ("allowed_timeframes", playbook.allowed_timeframes, preset.allowed_timeframes),
                ("allowed_sessions", playbook.allowed_sessions, preset.allowed_sessions)
            ]
            for field, curr_val, preset_val in playbook_checks:
                if curr_val != preset_val:
                    preset_drift_detected = True
                    preset_drift_fields.append({
                        "field_name": field,
                        "preset_value": preset_val,
                        "current_value": curr_val
                    })
                    
            if portfolio.risk_per_trade_pct != preset.default_portfolio_risk_pct:
                preset_drift_detected = True
                preset_drift_fields.append({
                    "field_name": "risk_per_trade_pct",
                    "preset_value": preset.default_portfolio_risk_pct,
                    "current_value": portfolio.risk_per_trade_pct
                })
                
    # Compile details of the report as JSON details
    details_dict = {
        "playbook_violations": [
            {
                "created_at": pe.get("created_at"),
                "symbol": pe.get("symbol"),
                "decision_state": pe.get("decision_state"),
                "details": pe.get("details_json")
            }
            for pe in playbook_events if pe.get("event_type") == "VIOLATION"
        ],
        "portfolio_blocks": [
            {
                "created_at": re.get("created_at"),
                "symbol": re.get("symbol"),
                "reason": re.get("reason"),
                "details": re.get("details_json")
            }
            for re in risk_events if re.get("risk_status") == "BLOCKED"
        ],
        "parameter_recommendation_alignment": [
            {
                "recommendation_id": rec.get("recommendation_id"),
                "symbol": rec.get("symbol"),
                "timeframe": rec.get("timeframe"),
                "robustness_score": rec.get("robustness_score"),
                "recommendation_status": rec.get("recommendation_status")
            }
            for rec in recommendations[:5]
        ],
        "active_preset_id": active_preset_id,
        "active_preset_name": active_preset_name,
        "preset_drift_detected": preset_drift_detected,
        "preset_drift_fields_json": json.dumps(preset_drift_fields)
    }
    
    return ComplianceReport(
        workspace_id=workspace_id,
        workspace_name=ws_name,
        start_date=start_date,
        end_date=end_date,
        compliance_score=score,
        metrics=metrics,
        generated_at=now_str,
        details_json=json.dumps(details_dict)
    )
