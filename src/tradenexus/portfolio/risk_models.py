from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PortfolioSettings:
    id: int = 1
    account_equity: float = 100000.0
    risk_per_trade_pct: float = 1.0
    max_daily_risk_pct: float = 3.0
    max_total_open_risk_pct: float = 5.0
    max_concurrent_trades: int = 5
    max_same_direction_trades: int = 3
    max_correlated_positions: int = 2
    correlation_threshold: float = 0.7
    correlation_lookback_bars: int = 50
    correlation_cache_ttl_seconds: int = 3600
    default_contract_multiplier: float = 1.0
    default_point_value: float = 1.0
    currency: str = "USD"
    notes: str = ""

@dataclass
class SymbolRiskProfile:
    symbol: str
    asset_class: str
    point_value: float = 1.0
    contract_multiplier: float = 1.0
    min_position_size: float = 0.01
    position_step: float = 0.01
    currency: str = "USD"
    updated_at: str = ""

@dataclass
class PositionSizeResult:
    risk_amount: float
    risk_points: float
    position_size_units: float
    estimated_loss_at_sl: float
    estimated_profit_tp1: float
    estimated_profit_tp2: float
    r_multiple_tp1: float
    r_multiple_tp2: float
    sizing_status: str
    sizing_warning: str

@dataclass
class ExposureSummary:
    realized_daily_risk: float
    total_open_risk: float
    total_open_risk_pct: float
    potential_setup_risk: float
    potential_setup_risk_pct: float
    risk_by_symbol: Dict[str, float] = field(default_factory=dict)
    risk_by_asset_class: Dict[str, float] = field(default_factory=dict)
    risk_by_direction: Dict[str, float] = field(default_factory=dict)
    number_of_active_trades: int = 0
    same_direction_trade_count: int = 0
    pending_actionable_setup_count: int = 0

@dataclass
class CorrelationRiskResult:
    correlation_matrix: Dict[str, Dict[str, float]]
    highly_correlated_pairs: List[tuple]
    same_direction_correlation_warnings: List[str]
    correlation_warning: str

@dataclass
class RiskLimitResult:
    risk_status: str  # "OK" / "WARNING" / "BLOCKED"
    reasons: List[str]
    warnings: List[str]
    blocked_actions: List[str]

@dataclass
class PortfolioSnapshot:
    snapshot_id: str
    created_at: str
    realized_daily_risk: float
    open_risk: float
    open_risk_pct: float
    potential_setup_risk: float
    potential_setup_risk_pct: float
    active_trade_count: int
    actionable_setup_count: int
    risk_status: str
    warnings_json: str
    details_json: str

@dataclass
class PortfolioRiskEvent:
    event_id: str
    created_at: str
    signal_id: Optional[str]
    trade_id: Optional[str]
    symbol: str
    event_type: str
    risk_status: str
    reason: str
    details_json: str
