import pytest
import streamlit as st
from tradenexus.signals.state import initialize_trade_state, start_trade, is_trade_active, clear_active_trade

def test_decision_states_tracker():
    """
    Verifies that the session state active trade position tracker transitions states correctly,
    and is_trade_active accurately blocks/enables the MANAGE TRADE state.
    """
    # Create mock session state values
    if "active_trade" not in st.session_state:
        st.session_state["active_trade"] = None
        
    # Start fresh
    clear_active_trade()
    assert not is_trade_active()
    
    # 1. Start active trade
    start_trade(
        symbol="BTC-USD",
        direction="BUY",
        entry=50000.0,
        sl=48000.0,
        tp1=53000.0,
        tp2=56000.0
    )
    assert is_trade_active()
    assert st.session_state["active_trade"]["status"] == "ACTIVE"
    
    # 2. Clear trade (e.g. SL hit)
    clear_active_trade()
    assert not is_trade_active()
