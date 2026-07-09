# TradeNexus Pro: Multi-Indicator Trading Dashboard

TradeNexus Pro is an advanced multi-indicator trading dashboard that fetches market data, performs multi-timeframe calculations, and displays real-time quantitative trading signals. Built using Streamlit, pandas, and plotly.

---

## 🚀 Features

- **Multi-Provider Data Layer**: Supports modular data providers (e.g., `yfinance` and fallbacks) with automatic retry and health logs.
- **Data Quality Assessor**: Inspects warmup bar depth and detects stale prices with active crypto vs equities weekend rules.
- **Multiple Timeframe (MTF) Engine**: Resamples base interval data dynamically (e.g. `15m`) to produce higher-timeframe data (`1h`, `4h`, `1d`) with correct OHLCV aggregation.
- **Traders Trend Dashboard (TTD)**: A consolidated multi-timeframe summary table displaying CDC ActionZone trend/signal states and MACD crossovers simultaneously across 15m, 1h, 4h, and 1D.
- **Integrated Technical Indicators**:
  - **CDC ActionZone (Simplified)**: Fast EMA 12 / Slow EMA 26 trend identification and crossover signal detection.
  - **MACD (MTF)**: Projecting MACD (12, 26, 9) calculations across resampled timeframes.
  - **Smart Money Concepts (SMC Lite)**: Swing highs/lows extraction via a 20-period rolling window to dynamically highlight Support and Resistance zones.
  - **MCDX (Proxy & Classic)**: Custom momentum strength oscillator (`RSI(14) * ATR(14)`) and institutional money flow.
- **Trading Playbook & Rule Enforcer**: Governs tradability based on session hours (Asia, London, NY) and discipline cooldown metrics without mutating technical signals.
- **Portfolio Risk Command Center**: Checks exposure correlation and calculates position size.

---

## 🛠️ Installation & Setup

1. **Clone or Navigate to Project Directory**:
   ```bash
   cd d:\TradeNexus
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   # On Windows:
   .\.venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables Config**:
   Copy `.env.example` to `.env` and fill in credentials:
   ```bash
   cp .env.example .env
   ```

---

## 💻 Running the Application

Launch the Streamlit web application:
```bash
streamlit run app.py
```

Open the web address in your browser (usually `http://localhost:8501`).

---

## 🐳 Docker Deployment

To deploy TradeNexus DSS inside a local containerized environment:

1. **Start the containerized service**:
   ```bash
   docker compose up --build -d
   ```
2. **Access application**:
   Navigate to `http://localhost:8501` in your browser.
3. **Database logs persistence**:
   SQLite database records are safely stored inside the docker named volume `tradenexus-data`.

---

## 🧪 Pre-Release Compliance Check

Before committing or releasing new changes, run the automated compliance checker script:
```bash
python scripts/release_check.py
```
This script validates that:
- Required deployment files exist.
- No forbidden files (`.venv`, database `.sqlite` files) are present in packaging targets.
- No hardcoded secrets (API tokens, webhooks) exist in Python source files.
- UI Entrypoints compile and import cleanly.
- The unit test suite passes cleanly.
