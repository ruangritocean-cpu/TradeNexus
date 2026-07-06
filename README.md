# TradeNexus Pro: Multi-Indicator Trading Dashboard

TradeNexus Pro is an advanced multi-indicator trading dashboard that fetches market data, performs multi-timeframe calculations, and displays real-time quantitative trading signals. Built using Streamlit, pandas, and plotly.

## 🚀 Features

- **Data Fetching Engine**: Connects to the Yahoo Finance API (`yfinance`) to retrieve high-resolution base candlestick data.
- **Multiple Timeframe (MTF) Engine**: Resamples base interval data dynamically (e.g. `15m`) to produce higher-timeframe data (`1h`, `4h`, `1d`) with correct OHLCV aggregation.
- **Traders Trend Dashboard (TTD)**: A consolidated multi-timeframe summary table displaying CDC ActionZone trend/signal states and MACD crossovers simultaneously across 15m, 1h, 4h, and 1D.
- **Integrated Technical Indicators**:
  - **CDC ActionZone (Simplified)**: Fast EMA 12 / Slow EMA 26 trend identification and crossover signal detection.
  - **MACD (MTF)**: Projecting MACD (12, 26, 9) calculations across multiple resampled timeframes.
  - **Smart Money Concepts (SMC Lite)**: Swing highs/lows extraction via a 20-period rolling window to dynamically highlight Support and Resistance zones.
  - **MCDX (Proxy & Classic)**: Custom momentum strength oscillator (`RSI(14) * ATR(14)`) and institutional/hot/retail money flow area chart.
  - **Adaptive Trend Finder**: Kaufman's Adaptive Moving Average (KAMA) and SuperTrend direction filters.

---

## 🛠️ Installation & Setup

1. **Clone or Navigate to Project Directory**:
   ```bash
   cd d:\TradeNexus
   ```

2. **Create a Virtual Environment** (Recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Running the Application

Launch the Streamlit web application:
```bash
streamlit run app.py
```

Open the local address printed by Streamlit in your web browser (usually `http://localhost:8501`).

---

## ⚙️ Project File Structure

- `app.py`: Streamlit application interface layout and main workflow.
- `data_manager.py`: Connects to `yfinance` to fetch OHLCV data with API boundary handling.
- `mtf_engine.py`: Dynamic pandas resampling engine.
- `indicators.py`: Technical indicator calculations.
- `ui_components.py`: Renders custom TTD HTML tables, and Plotly interactive subplots.
- `requirements.txt`: Python package dependency list.
