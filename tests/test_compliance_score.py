import pytest
from tradenexus.reports.compliance_models import ComplianceMetrics
from tradenexus.reports.compliance_engine import calculate_compliance_score

def test_compliance_score_deductions():
    # 1. Clean report should yield 100.0
    metrics = ComplianceMetrics(total_signals=0)
    assert calculate_compliance_score(metrics) == 100.0
    
    metrics.total_signals = 10
    assert calculate_compliance_score(metrics) == 100.0
    
    # 2. Playbook violations deduct 5 points each
    metrics.playbook_violation_count = 1
    assert calculate_compliance_score(metrics) == 95.0
    
    metrics.playbook_violation_count = 2
    assert calculate_compliance_score(metrics) == 90.0
    
    # Max playbook violation penalty is 25.0 points
    metrics.playbook_violation_count = 6
    assert calculate_compliance_score(metrics) == 75.0
    
    # 3. Portfolio risk blocks deduct 10 points each
    metrics_portfolio = ComplianceMetrics(total_signals=10, alerts_blocked_portfolio=1)
    assert calculate_compliance_score(metrics_portfolio) == 90.0
    
    # Max portfolio penalty is 25.0 points
    metrics_portfolio.alerts_blocked_portfolio = 3
    assert calculate_compliance_score(metrics_portfolio) == 75.0
    
    # 4. Invalid data reduces score scaled by percentage of invalid signals (max 15.0 points)
    # If 50% of signals are invalid, deducts 7.5 points
    metrics_data = ComplianceMetrics(total_signals=10, signals_invalid_data=5)
    assert calculate_compliance_score(metrics_data) == 92.5
    
    # If 100% of signals are invalid, deducts 15.0 points
    metrics_data.signals_invalid_data = 10
    assert calculate_compliance_score(metrics_data) == 85.0
