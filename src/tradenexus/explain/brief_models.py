from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class BriefRiskPlan:
    entry: float
    sl: float
    tp1: float
    tp2: float
    rr_tp1: float
    position_size: float = 0.0
    risk_amount: float = 0.0

@dataclass
class BriefPortfolioCheck:
    portfolio_risk_status: str  # "OK", "WARNING", "BLOCKED"
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class BriefInvalidation:
    condition: str
    price_level: float
    notes: str

@dataclass
class DecisionBrief:
    symbol: str
    timeframe: str
    decision_state: str
    direction: str
    alignment_type: str
    confluence_score: float
    primary_regime: str
    regime_flags: List[str] = field(default_factory=list)
    risk_plan: Optional[BriefRiskPlan] = None
    portfolio_check: Optional[BriefPortfolioCheck] = None
    invalidation_conditions: List[BriefInvalidation] = field(default_factory=list)
    headline: str = ""
    summary: str = ""
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    next_action: str = ""
    created_at: str = ""
