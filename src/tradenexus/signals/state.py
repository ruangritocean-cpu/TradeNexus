import streamlit as st
import datetime

def initialize_trade_state():
    """
    Initializes active trade position state tracking inside Streamlit's session state.
    """
    if "active_trade" not in st.session_state:
        st.session_state["active_trade"] = None

def start_trade(symbol: str, direction: str, entry: float, sl: float, tp1: float, tp2: float):
    """
    Saves an active trade position state.
    """
    st.session_state["active_trade"] = {
        "symbol": symbol,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "entry_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "ACTIVE"
    }

def update_trade_status(status: str):
    """
    Updates status: ACTIVE / TP1_HIT / TP2_HIT / SL_HIT / CLOSED.
    """
    if st.session_state.get("active_trade"):
        st.session_state["active_trade"]["status"] = status
        # If position is resolved, clear it
        if status in ["SL_HIT", "TP2_HIT", "CLOSED"]:
            st.session_state["active_trade"] = None

def get_active_trade() -> dict:
    """
    Returns the active trade dictionary if it exists.
    """
    return st.session_state.get("active_trade")

def is_trade_active() -> bool:
    """
    Checks if there is a valid, active trade position.
    """
    trade = get_active_trade()
    return trade is not None and trade.get("status") in ["ACTIVE", "TP1_HIT"]

def clear_active_trade():
    """
    Clears the active trade position.
    """
    st.session_state["active_trade"] = None
