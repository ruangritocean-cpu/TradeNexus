import sys
import os
import streamlit as st

# Set page config as the absolute first Streamlit operation to enforce wide layout
st.set_page_config(page_title="TradeNexus Pro", page_icon="📈", layout="wide")

# Ensure the src folder is in the Python lookup path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from tradenexus.ui.dashboard import run_dashboard

if __name__ == "__main__":
    run_dashboard()

# Trigger Streamlit Cloud hot-reload and module cache refresh: 2026-07-09 12:40
