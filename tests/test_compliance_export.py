import pytest
import json
from tradenexus.reports.compliance_models import ComplianceMetrics, ComplianceReport
from tradenexus.reports.report_export import export_report_to_csv, export_report_to_json

def test_compliance_export_formats():
    metrics = ComplianceMetrics(
        total_signals=15,
        alerts_sent=5,
        win_rate=0.6,
        expectancy=1.5,
        profit_factor=2.0,
        max_drawdown=1.2
    )
    
    report = ComplianceReport(
        workspace_id="crypto_desk",
        workspace_name="Crypto Desk Workspace",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        compliance_score=92.5,
        metrics=metrics,
        generated_at="2026-07-09T15:00:00Z",
        details_json=json.dumps({
            "playbook_violations": [],
            "portfolio_blocks": []
        })
    )
    
    # 1. Test CSV Export contains only this workspace
    csv_str = export_report_to_csv(report)
    assert "Crypto Desk Workspace" in csv_str
    assert "crypto_desk" in csv_str
    assert "92.5/100.0" in csv_str
    assert "1.50R" in csv_str
    assert "60.0%" in csv_str
    assert "other_workspace" not in csv_str
    
    # 2. Test JSON Export contains only this workspace
    json_str = export_report_to_json(report)
    data = json.loads(json_str)
    assert data["workspace_id"] == "crypto_desk"
    assert data["workspace_name"] == "Crypto Desk Workspace"
    assert data["compliance_score"] == 92.5
    assert data["metrics"]["win_rate"] == 0.6
    assert "other_workspace" not in json_str
