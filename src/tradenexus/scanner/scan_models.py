from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class WatchlistItem:
    symbol: str
    display_name: str
    asset_class: str
    enabled: bool = True
    preferred_timeframes: List[str] = field(default_factory=lambda: ["1h", "4h"])
    min_confluence_score: float = 70.0
    min_rr: float = 1.5
    alert_enabled: bool = True
    alert_ready_enabled: bool = False
    alert_entry_enabled: bool = True
    notes: str = ""
    workspace_id: str = "default_workspace"

@dataclass
class ScanRun:
    scan_run_id: str
    started_at: str
    finished_at: str
    status: str
    total_symbols: int
    success_count: int
    warning_count: int
    error_count: int
    skipped_count: int
    config_json: str
    workspace_id: str = "default_workspace"

@dataclass
class ScanResult:
    scan_run_id: str
    symbol: str
    timeframe: str
    scan_time: str
    symbol_status: str
    decision_state: str
    direction: str
    alignment_type: str
    confluence_score: float
    rr_tp1: float
    primary_regime: str
    regime_flags_json: str
    data_quality_status: str
    alert_status: str
    journal_status: str
    reasons_json: str
    warnings_json: str
    error_message: str
    created_at: str
    signal_id: Optional[str] = None
    id: Optional[int] = None
    position_size_units: float = 0.0
    candidate_risk_amount: float = 0.0
    candidate_risk_pct: float = 0.0
    provider_used: Optional[str] = "unknown"
    fallback_used: int = 0
    data_quality_warnings_json: str = "[]"
    data_quality_errors_json: str = "[]"
    latest_candle_time: Optional[str] = None
    bars_available: int = 0
    workspace_id: str = "default_workspace"
