from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class StrategyPreset:
    preset_id: str
    workspace_id: str
    name: str
    description: str
    asset_class: str
    trading_style: str
    risk_profile: str
    allowed_symbols: List[str] = field(default_factory=list)
    allowed_timeframes: List[str] = field(default_factory=list)
    allowed_sessions: List[str] = field(default_factory=list)
    allowed_setup_types: List[str] = field(default_factory=list)
    allowed_regimes: List[str] = field(default_factory=list)
    blocked_regimes: List[str] = field(default_factory=list)
    min_confluence_score: float = 70.0
    min_rr: float = 1.5
    max_trades_per_day: int = 5
    max_losses_per_day: int = 3
    max_consecutive_losses: int = 3
    cooldown_minutes_after_loss: int = 60
    default_portfolio_risk_pct: float = 1.0
    suggested_symbols: List[str] = field(default_factory=list)
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    is_builtin: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class PresetApplyRecord:
    apply_id: str
    preset_id: str
    workspace_id: str
    applied_at: str
    applied_sections: List[str]
    previous_values: str  # JSON String of previous state
    new_values: str       # JSON String of new applied state
    warnings: List[str]   # JSON String or List of warnings during apply
    applied_by_label: str = "User"
