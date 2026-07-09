import csv
import io
import json
from typing import Dict, Any
from tradenexus.reports.compliance_models import ComplianceReport

def export_report_to_csv(report: ComplianceReport) -> str:
    """
    Exports ComplianceReport details into a clean CSV format string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 1. Title & Meta Section
    writer.writerow(["=================================================="])
    writer.writerow(["TRADENEXUS PLAN COMPLIANCE & PERFORMANCE REPORT"])
    writer.writerow(["=================================================="])
    writer.writerow([])
    writer.writerow(["Workspace Name", report.workspace_name])
    writer.writerow(["Workspace ID", report.workspace_id])
    writer.writerow(["Start Date (UTC)", report.start_date])
    writer.writerow(["End Date (UTC)", report.end_date])
    writer.writerow(["Compliance Score", f"{report.compliance_score:.1f}/100.0"])
    writer.writerow(["Generated At (UTC)", report.generated_at])
    writer.writerow([])
    
    # 2. Compliance Metrics Section
    writer.writerow(["--------------------------------------------------"])
    writer.writerow(["COMPLIANCE & DISCIPLINE METRICS"])
    writer.writerow(["--------------------------------------------------"])
    m = report.metrics
    writer.writerow(["Total Signals Scanned", m.total_signals])
    writer.writerow(["Actionable Signals Found", m.actionable_signals])
    writer.writerow(["Alerts Dispatched Successfully", m.alerts_sent])
    writer.writerow(["Alerts Blocked by Playbook rules", m.alerts_blocked_playbook])
    writer.writerow(["Alerts Blocked by Portfolio risk rules", m.alerts_blocked_portfolio])
    writer.writerow(["Signals with Invalid Data", m.signals_invalid_data])
    writer.writerow(["Signals with Data Quality Warnings", m.signals_data_warnings])
    writer.writerow(["Playbook Violation Count", m.playbook_violation_count])
    writer.writerow(["- Session Violations", m.session_violations])
    writer.writerow(["- Cooldown Violations", m.cooldown_violations])
    writer.writerow(["- Overtrading/Limits Warnings", m.overtrading_warnings])
    writer.writerow(["- Low Confluence Violations", m.low_confluence_violations])
    writer.writerow(["- Low RR Ratio Violations", m.low_rr_violations])
    writer.writerow([])
    
    # 3. Performance Metrics Section
    writer.writerow(["--------------------------------------------------"])
    writer.writerow(["TRADING PERFORMANCE SUMMARY"])
    writer.writerow(["--------------------------------------------------"])
    writer.writerow(["Trades Opened", m.trades_opened])
    writer.writerow(["Trades Closed", m.trades_closed])
    writer.writerow(["Win Rate", f"{m.win_rate * 100:.1f}%"])
    writer.writerow(["Expectancy (R-multiple)", f"{m.expectancy:.2f}R"])
    writer.writerow(["Profit Factor", f"{m.profit_factor:.2f}"])
    writer.writerow(["Max Drawdown (R-multiple)", f"{m.max_drawdown:.2f}R"])
    writer.writerow(["Average Confluence Score", f"{m.average_confluence:.1f}"])
    writer.writerow(["Average Risk-to-Reward Ratio", f"{m.average_rr:.2f}"])
    writer.writerow([])
    
    # 4. Details Section (Violations & Blocks)
    try:
        details = json.loads(report.details_json)
    except Exception:
        details = {}
        
    violations = details.get("playbook_violations", [])
    if violations:
        writer.writerow(["--------------------------------------------------"])
        writer.writerow(["PLAYBOOK VIOLATION ENTRIES DETAILED"])
        writer.writerow(["--------------------------------------------------"])
        writer.writerow(["Timestamp", "Symbol", "Decision State", "Message"])
        for v in violations:
            try:
                msg = json.loads(v.get("details", "{}")).get("message", "")
            except Exception:
                msg = ""
            writer.writerow([v.get("created_at"), v.get("symbol"), v.get("decision_state"), msg])
        writer.writerow([])
            
    blocks = details.get("portfolio_blocks", [])
    if blocks:
        writer.writerow(["--------------------------------------------------"])
        writer.writerow(["PORTFOLIO RISK BLOCK ENTRIES DETAILED"])
        writer.writerow(["--------------------------------------------------"])
        writer.writerow(["Timestamp", "Symbol", "Block Reason"])
        for b in blocks:
            writer.writerow([b.get("created_at"), b.get("symbol"), b.get("reason")])
            
    return output.getvalue()

def export_report_to_json(report: ComplianceReport) -> str:
    """
    Exports ComplianceReport details into a serialized JSON format string.
    """
    report_dict = {
        "workspace_id": report.workspace_id,
        "workspace_name": report.workspace_name,
        "start_date": report.start_date,
        "end_date": report.end_date,
        "compliance_score": report.compliance_score,
        "generated_at": report.generated_at,
        "metrics": {
            "total_signals": report.metrics.total_signals,
            "actionable_signals": report.metrics.actionable_signals,
            "alerts_sent": report.metrics.alerts_sent,
            "alerts_blocked_portfolio": report.metrics.alerts_blocked_portfolio,
            "alerts_blocked_playbook": report.metrics.alerts_blocked_playbook,
            "signals_invalid_data": report.metrics.signals_invalid_data,
            "signals_data_warnings": report.metrics.signals_data_warnings,
            "trades_opened": report.metrics.trades_opened,
            "trades_closed": report.metrics.trades_closed,
            "win_rate": report.metrics.win_rate,
            "expectancy": report.metrics.expectancy,
            "profit_factor": report.metrics.profit_factor,
            "max_drawdown": report.metrics.max_drawdown,
            "average_rr": report.metrics.average_rr,
            "average_confluence": report.metrics.average_confluence,
            "playbook_violation_count": report.metrics.playbook_violation_count,
            "overtrading_warnings": report.metrics.overtrading_warnings,
            "cooldown_violations": report.metrics.cooldown_violations,
            "session_violations": report.metrics.session_violations,
            "low_rr_violations": report.metrics.low_rr_violations,
            "low_confluence_violations": report.metrics.low_confluence_violations
        },
        "details": json.loads(report.details_json)
    }
    return json.dumps(report_dict, indent=4)
