import pytest
from tradenexus.reports.compliance_models import ComplianceMetrics, ComplianceReport

def test_compliance_models_instantiation():
    """
    Verifies instantiation of compliance dataclasses and default values.
    """
    metrics = ComplianceMetrics()
    assert metrics.total_signals == 0
    assert metrics.win_rate == 0.0
    assert metrics.expectancy == 0.0
    
    report = ComplianceReport(
        workspace_id="test_ws",
        workspace_name="Test Workspace",
        start_date="2026-07-09T00:00:00Z",
        end_date="2026-07-09T23:59:59Z",
        compliance_score=85.5,
        metrics=metrics,
        generated_at="2026-07-09T12:00:00Z"
    )
    assert report.workspace_id == "test_ws"
    assert report.compliance_score == 85.5
    assert report.metrics.total_signals == 0
