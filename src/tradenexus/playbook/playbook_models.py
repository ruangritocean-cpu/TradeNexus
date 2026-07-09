from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Playbook:
    playbook_id: str
    name: str
    enabled: int = 1
    allowed_symbols: List[str] = field(default_factory=list)
    allowed_asset_classes: List[str] = field(default_factory=list)
    allowed_timeframes: List[str] = field(default_factory=list)
    allowed_setup_types: List[str] = field(default_factory=list)
    min_confluence_score: float = 70.0
    min_rr: float = 1.5
    allowed_regimes: List[str] = field(default_factory=list)
    blocked_regimes: List[str] = field(default_factory=list)
    max_trades_per_day: int = 5
    max_losses_per_day: int = 3
    max_consecutive_losses: int = 3
    allowed_sessions: List[str] = field(default_factory=list)
    cooldown_minutes_after_loss: int = 60
    created_at: Optional[str] = None
    notes: str = ""
    workspace_id: str = "default_workspace"
    active_preset_id: Optional[str] = None

@dataclass
class PlaybookRuleEvent:
    event_id: str
    created_at: str
    playbook_id: str
    symbol: str
    rule_name: str
    event_type: str  # 'VIOLATION', 'WARNING', 'PASS'
    decision_state: str
    details_json: str
    workspace_id: str = "default_workspace"

@dataclass
class DailyTradingState:
    date: str  # 'YYYY-MM-DD'
    trades_count: int = 0
    losses_count: int = 0
    consecutive_losses: int = 0
    last_loss_time: Optional[str] = None
    updated_at: Optional[str] = None
    workspace_id: str = "default_workspace"
