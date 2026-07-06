from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Signal:
    signal_id: str
    symbol: str
    timeframe: str
    candle_close_time: str
    decision_state: str
    direction: str
    alignment_type: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    rr_tp1: float
    rr_tp2: float
    confluence_score: float
    directional_score: float
    quality_score: float
    market_bias: str
    setup_direction: str
    trigger_direction: str
    execution_direction: str
    smc_support_source: str
    smc_resistance_source: str
    data_quality_valid: int  # 1 or 0
    is_actionable: int       # 1 or 0
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    outcome_status: str = "OPEN"
    outcome_time: Optional[str] = None
    bars_to_outcome: Optional[int] = None
    realized_r_multiple: float = 0.0
    created_at: Optional[str] = None
    
    # Sprint 4 additions
    primary_regime: str = "UNKNOWN"
    regime_flags: str = ""
    regime_score: float = 0.0
    volume_confirmation: str = "NEUTRAL"
    vwap_alignment: str = "NEUTRAL"
    bos_present: int = 0
    choch_present: int = 0
    fvg_present: int = 0
    liquidity_sweep_present: int = 0

@dataclass
class AlertLog:
    id: Optional[int]
    signal_id: str
    provider: str
    status: str
    sent_at: str
    error_message: Optional[str] = None

@dataclass
class Trade:
    trade_id: str
    signal_id: str
    symbol: str
    direction: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    status: str
    opened_at: str
    closed_at: Optional[str] = None
    realized_r_multiple: float = 0.0
