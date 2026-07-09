from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ComplianceMetrics:
    total_signals: int = 0
    actionable_signals: int = 0
    alerts_sent: int = 0
    alerts_blocked_portfolio: int = 0
    alerts_blocked_playbook: int = 0
    signals_invalid_data: int = 0
    signals_data_warnings: int = 0
    trades_opened: int = 0
    trades_closed: int = 0
    win_rate: float = 0.0
    expectancy: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    average_rr: float = 0.0
    average_confluence: float = 0.0
    playbook_violation_count: int = 0
    overtrading_warnings: int = 0
    cooldown_violations: int = 0
    session_violations: int = 0
    low_rr_violations: int = 0
    low_confluence_violations: int = 0

@dataclass
class ComplianceReport:
    workspace_id: str
    workspace_name: str
    start_date: str
    end_date: str
    compliance_score: float
    metrics: ComplianceMetrics
    generated_at: str
    details_json: str = "{}"
