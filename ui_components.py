import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def render_ttd_dashboard(ttd_data: dict):
    """
    Renders the Traders Trend Dashboard (TTD) table.
    
    Args:
        ttd_data (dict): Dictionary where keys are timeframes and values are the latest row data dict.
    """
    rows = []
    for tf, data in ttd_data.items():
        if data is None or empty_dict(data):
            rows.append({
                "Timeframe": tf,
                "CDC Trend": "N/A",
                "CDC Signal": "N/A",
                "MACD Line": "N/A",
                "MACD Signal": "N/A",
                "MACD Hist": "N/A",
                "MACD Trend": "N/A",
                "Adaptive Trend": "N/A"
            })
            continue
            
        rows.append({
            "Timeframe": tf,
            "CDC Trend": data.get("CDC_Trend", "Neutral"),
            "CDC Signal": data.get("CDC_Signal", "Hold"),
            "MACD Line": f"{data.get('MACD', 0.0):.2f}",
            "MACD Signal": f"{data.get('MACD_Signal', 0.0):.2f}",
            "MACD Hist": f"{data.get('MACD_Hist', 0.0):.2f}",
            "MACD Trend": data.get("MACD_Trend", "Neutral"),
            "Adaptive Trend": data.get("SuperTrend_Direction", data.get("Adaptive_Trend", "Neutral")),
            "ADX": data.get("ADX", 20.0),
            "ADX Strength": data.get("ADX_Strength", "Sideways"),
            "BB Squeeze": data.get("BB_Squeeze", False)
        })
        
    df_ttd = pd.DataFrame(rows)
    
    # Custom HTML styling for premium look
    html_code = """
    <style>
    .ttd-table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
        font-size: 0.95em;
        font-family: 'Outfit', 'Inter', sans-serif;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 0 20px rgba(0,0,0,0.15);
        background-color: #0E1117;
    }
    .ttd-table thead tr {
        background-color: #1F2937;
        color: #F3F4F6;
        text-align: left;
        font-weight: bold;
    }
    .ttd-table th, .ttd-table td {
        padding: 12px 15px;
        text-align: center;
        border-bottom: 1px solid #374151;
    }
    .ttd-table tbody tr {
        border-bottom: 1px solid #1F2937;
    }
    .ttd-table tbody tr:hover {
        background-color: #2D3748;
    }
    .trend-bullish {
        color: #10B981;
        background-color: rgba(16, 185, 129, 0.15);
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .trend-bearish {
        color: #EF4444;
        background-color: rgba(239, 68, 68, 0.15);
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .sig-buy {
        color: #059669;
        border: 1px solid #10B981;
        background-color: rgba(16, 185, 129, 0.05);
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    .sig-sell {
        color: #DC2626;
        border: 1px solid #EF4444;
        background-color: rgba(239, 68, 68, 0.05);
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    .sig-hold {
        color: #9CA3AF;
        padding: 2px 6px;
    }
    .bb-squeeze {
        color: #F59E0B;
        background-color: rgba(245, 158, 11, 0.15);
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .bb-normal {
        color: #9CA3AF;
        padding: 4px 8px;
    }
    .adx-strong {
        color: #34D399;
        font-weight: 700;
    }
    .adx-weak {
        color: #EF4444;
        font-weight: 700;
    }
    .adx-neutral {
        color: #9CA3AF;
    }
    </style>
    <table class="ttd-table">
        <thead>
            <tr>
                <th>Timeframe</th>
                <th>CDC Trend</th>
                <th>CDC Signal</th>
                <th>MACD Line</th>
                <th>MACD Signal</th>
                <th>MACD Hist</th>
                <th>MACD Trend</th>
                <th>Adaptive Trend</th>
                <th>ADX Strength</th>
                <th>Bollinger Bands</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for row in rows:
        cdc_trend_cls = "trend-bullish" if row["CDC Trend"] == "Bullish" else ("trend-bearish" if row["CDC Trend"] == "Bearish" else "")
        macd_trend_cls = "trend-bullish" if row["MACD Trend"] == "Bullish" else ("trend-bearish" if row["MACD Trend"] == "Bearish" else "")
        adapt_trend_cls = "trend-bullish" if row["Adaptive Trend"] == "Bullish" else ("trend-bearish" if row["Adaptive Trend"] == "Bearish" else "")
        
        sig_cls = "sig-hold"
        if row["CDC Signal"] == "Buy":
            sig_cls = "sig-buy"
        elif row["CDC Signal"] == "Sell":
            sig_cls = "sig-sell"
            
        # ADX classes
        adx_val = row.get("ADX", 20.0)
        adx_str = row.get("ADX Strength", "Sideways")
        if adx_str == "Strong Trend":
            adx_cls = "adx-strong"
        elif adx_str == "Sideways":
            adx_cls = "adx-weak"
        else:
            adx_cls = "adx-neutral"
            
        # BB classes
        bb_squeeze = row.get("BB Squeeze", False)
        bb_text = "SQUEEZE ⚡" if bb_squeeze else "Normal"
        bb_cls = "bb-squeeze" if bb_squeeze else "bb-normal"
            
        html_code += f"""
            <tr>
                <td><strong>{row['Timeframe']}</strong></td>
                <td><span class="{cdc_trend_cls}">{row['CDC Trend']}</span></td>
                <td><span class="{sig_cls}">{row['CDC Signal']}</span></td>
                <td>{row['MACD Line']}</td>
                <td>{row['MACD Signal']}</td>
                <td>{row['MACD Hist']}</td>
                <td><span class="{macd_trend_cls}">{row['MACD Trend']}</span></td>
                <td><span class="{adapt_trend_cls}">{row['Adaptive Trend']}</span></td>
                <td><span class="{adx_cls}">{adx_val:.1f} ({adx_str})</span></td>
                <td><span class="{bb_cls}">{bb_text}</span></td>
            </tr>
        """
        
    html_code += """
        </tbody>
    </table>
    """
    # Clean up whitespace from each line to prevent Markdown from parsing HTML as code blocks
    clean_html = "\n".join([line.strip() for line in html_code.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)

def empty_dict(d: dict) -> bool:
    return len(d) == 0

def draw_advanced_charts(df: pd.DataFrame, ticker: str, timeframe: str, strategy: dict = None):
    """
    Draws a Plotly figure with 4 subplots:
    1. Candlestick chart + EMAs (CDC ActionZone) + SMC Support/Resistance + KAMA
    2. MACD MTF (MACD line, Signal line, Histogram)
    3. Custom MCDX Proxy (RSI * ATR)
    4. Classic MCDX Smart Money Flow (Bankers/Hot Money/Retailer)
    """
    if df.empty:
        st.warning("No data to display in chart.")
        return
        
    # Standardizing columns
    df = df.copy()
    
    # Keep last 150 bars for better visibility
    plot_df = df.tail(150)
    
    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=(
            f"{ticker} - {timeframe} | Price, CDC ActionZone & SMC Zones",
            "MACD (12, 26, 9)",
            "MCDX Proxy (RSI 14 * ATR 14) Momentum Strength",
            "MCDX Smart Money Flow (%)"
        )
    )
    
    # ------------------ Row 1: Candlestick & CDC & KAMA & SMC ------------------
    # CDC ActionZone color mapping for candlesticks
    # Green = EMA12 > EMA26, Red = EMA12 < EMA26
    # Optional colors for Buy/Sell signals (e.g. bright green / bright red)
    
    colors = []
    for idx, row in plot_df.iterrows():
        if row.get("CDC_Trend") == "Bullish":
            colors.append("#10B981") # Green
        else:
            colors.append("#EF4444") # Red
            
    # Bollinger Bands (drawn in background behind candlesticks)
    if "BBU" in plot_df.columns and "BBL" in plot_df.columns:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["BBU"], 
                name="BB Upper", 
                line=dict(color="rgba(148, 163, 184, 0.35)", width=1.2)
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["BBL"], 
                name="BB Lower", 
                line=dict(color="rgba(148, 163, 184, 0.35)", width=1.2),
                fill="tonexty", 
                fillcolor="rgba(148, 163, 184, 0.04)"
            ),
            row=1, col=1
        )
        if "BBM" in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index, y=plot_df["BBM"], 
                    name="BB Basis (SMA 20)", 
                    line=dict(color="rgba(244, 63, 94, 0.35)", width=1, dash="dash")
                ),
                row=1, col=1
            )
            
    fig.add_trace(
        go.Candlestick(
            x=plot_df.index,
            open=plot_df["Open"],
            high=plot_df["High"],
            low=plot_df["Low"],
            close=plot_df["Close"],
            name="OHLC",
            increasing_line_color="#10B981",
            decreasing_line_color="#EF4444",
            increasing_fillcolor="rgba(16, 185, 129, 0.2)",
            decreasing_fillcolor="rgba(239, 68, 68, 0.2)"
        ),
        row=1, col=1
    )
    
    # EMA Fast (12) and EMA Slow (26)
    if "EMA_Fast" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["EMA_Fast"], name="EMA 12 (Fast)", line=dict(color="#60A5FA", width=1.5)),
            row=1, col=1
        )
    if "EMA_Slow" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["EMA_Slow"], name="EMA 26 (Slow)", line=dict(color="#F59E0B", width=1.5)),
            row=1, col=1
        )
        
    # KAMA or Adaptive Trend Finder
    if "KAMA" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["KAMA"], name="KAMA", line=dict(color="#C084FC", width=1, dash="dash")),
            row=1, col=1
        )
        
    # SMC Support/Resistance lines
    if "Support_Level" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["Support_Level"], name="SMC Support", line=dict(color="#059669", width=1.5, dash="dot")),
            row=1, col=1
        )
    if "Resistance_Level" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["Resistance_Level"], name="SMC Resistance", line=dict(color="#DC2626", width=1.5, dash="dot")),
            row=1, col=1
        )
        
    # Add strategy level lines on chart if provided
    if strategy is not None:
        entry = strategy.get("Entry", 0.0)
        sl = strategy.get("StopLoss", 0.0)
        tp1 = strategy.get("TakeProfit1", 0.0)
        tp2 = strategy.get("TakeProfit2", 0.0)
        
        if entry > 0:
            fig.add_trace(
                go.Scatter(x=plot_df.index, y=[entry]*len(plot_df), name="Entry Price", line=dict(color="#3B82F6", width=1.5, dash="dash")),
                row=1, col=1
            )
        if sl > 0:
            fig.add_trace(
                go.Scatter(x=plot_df.index, y=[sl]*len(plot_df), name="Stop Loss (SL)", line=dict(color="#EF4444", width=1.5, dash="dash")),
                row=1, col=1
            )
        if tp1 > 0:
            fig.add_trace(
                go.Scatter(x=plot_df.index, y=[tp1]*len(plot_df), name="Take Profit 1 (TP1)", line=dict(color="#10B981", width=1.5, dash="dash")),
                row=1, col=1
            )
        if tp2 > 0:
            fig.add_trace(
                go.Scatter(x=plot_df.index, y=[tp2]*len(plot_df), name="Take Profit 2 (TP2)", line=dict(color="#059669", width=1.5, dash="dash")),
                row=1, col=1
            )
        
    # Add Swing points markers
    swing_highs = plot_df[plot_df["Swing_High"].notna()]
    if not swing_highs.empty:
        fig.add_trace(
            go.Scatter(
                x=swing_highs.index, y=swing_highs["Swing_High"],
                mode="markers+text",
                marker=dict(symbol="triangle-down", size=8, color="#EF4444"),
                text="Swing High", textposition="top center",
                name="Swing High"
            ),
            row=1, col=1
        )
        
    swing_lows = plot_df[plot_df["Swing_Low"].notna()]
    if not swing_lows.empty:
        fig.add_trace(
            go.Scatter(
                x=swing_lows.index, y=swing_lows["Swing_Low"],
                mode="markers+text",
                marker=dict(symbol="triangle-up", size=8, color="#10B981"),
                text="Swing Low", textposition="bottom center",
                name="Swing Low"
            ),
            row=1, col=1
        )

    # ------------------ Row 2: MACD ------------------
    if "MACD" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["MACD"], name="MACD", line=dict(color="#60A5FA", width=1.5)),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["MACD_Signal"], name="Signal", line=dict(color="#F59E0B", width=1.5)),
            row=2, col=1
        )
        # Histogram
        hist_colors = np.where(plot_df["MACD_Hist"] >= 0, "#10B981", "#EF4444")
        fig.add_trace(
            go.Bar(x=plot_df.index, y=plot_df["MACD_Hist"], name="Histogram", marker_color=hist_colors),
            row=2, col=1
        )

    # ------------------ Row 3: MCDX Proxy (Oscillator) ------------------
    if "MCDX_Proxy" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["MCDX_Proxy"], name="MCDX Proxy", line=dict(color="#F472B6", width=2)),
            row=3, col=1
        )
        
    # ------------------ Row 4: Classic MCDX (Smart Money Flow Stacked) ------------------
    if "MCDX_Smart" in plot_df.columns:
        # Stacked area chart to show Banker (Red), Hot Money (Yellow), Retail (Green)
        # We plot Retail, Retail+Hot, and 100% to create stacked effect
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["MCDX_Smart"],
                mode="lines", line=dict(width=0.5, color="#EF4444"),
                fill="tozeroy", fillcolor="rgba(239, 68, 68, 0.6)",
                name="Smart Money (Bankers)", stackgroup="one"
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["MCDX_Hot"],
                mode="lines", line=dict(width=0.5, color="#FBBF24"),
                fill="tonexty", fillcolor="rgba(251, 191, 36, 0.6)",
                name="Hot Money (Speculators)", stackgroup="one"
            ),
            row=4, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=plot_df.index, y=plot_df["MCDX_Retail"],
                mode="lines", line=dict(width=0.5, color="#10B981"),
                fill="tonexty", fillcolor="rgba(16, 185, 129, 0.6)",
                name="Retail Money (Retailers)", stackgroup="one"
            ),
            row=4, col=1
        )
        
    # Design Aesthetics & Styling
    fig.update_layout(
        template="plotly_dark",
        height=900,
        margin=dict(l=50, r=30, t=50, b=50),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor="#0E1117",
        paper_bgcolor="#0E1117"
    )
    
    # Hide rangeslider for all subplots
    fig.update_xaxes(rangeslider_visible=False)
    
    # Update axes styling
    fig.update_xaxes(showgrid=True, gridcolor="#374151", linecolor="#4B5563")
    fig.update_yaxes(showgrid=True, gridcolor="#374151", linecolor="#4B5563")
    
    # Render in Streamlit
    st.plotly_chart(fig, use_container_width=True)

def render_trading_strategy_panel(strategy: dict):
    """
    Renders an actionable trading strategy panel with entry, TP, and SL details.
    
    Args:
        strategy (dict): Trading strategy details generated by indicators.generate_trading_signal.
    """
    decision = strategy.get("Decision", "NEUTRAL")
    confidence = strategy.get("Confidence", 50)
    entry = strategy.get("Entry", 0.0)
    sl = strategy.get("StopLoss", 0.0)
    tp1 = strategy.get("TakeProfit1", 0.0)
    tp2 = strategy.get("TakeProfit2", 0.0)
    warning = strategy.get("Warning", "ตลาดเคลื่อนไหวปกติเชิงโครงสร้าง")
    
    # CSS background styles depending on decision
    if "STRONG BUY" in decision:
        bg_color = "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(59, 130, 246, 0.1) 100%)"
        border_color = "#10B981"
        badge_color = "#10B981"
        text_desc = "สัญญาณซื้อแข็งแกร่ง (Strong Buy): CDC ActionZone, MACD และ SuperTrend มีความสอดคล้องกันเชิงบวกทั้งหมด"
    elif "BUY" in decision:
        bg_color = "linear-gradient(135deg, rgba(52, 211, 153, 0.1) 0%, rgba(15, 23, 42, 0.5) 100%)"
        border_color = "#34D399"
        badge_color = "#34D399"
        text_desc = "สัญญาณซื้อ (Buy): CDC ActionZone บ่งชี้แนวโน้มขาขึ้นเป็นบวกแล้ว"
    elif "STRONG SELL" in decision:
        bg_color = "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%)"
        border_color = "#EF4444"
        badge_color = "#EF4444"
        text_desc = "สัญญาณขายแข็งแกร่ง (Strong Sell): CDC ActionZone, MACD และ SuperTrend มีความสอดคล้องกันเชิงลบทั้งหมด"
    elif "SELL" in decision:
        bg_color = "linear-gradient(135deg, rgba(248, 113, 113, 0.1) 0%, rgba(15, 23, 42, 0.5) 100%)"
        border_color = "#F87171"
        badge_color = "#F87171"
        text_desc = "สัญญาณขาย (Sell): CDC ActionZone บ่งชี้แนวโน้มขาลงเป็นลบแล้ว"
    else:
        bg_color = "linear-gradient(135deg, rgba(107, 114, 128, 0.1) 0%, rgba(15, 23, 42, 0.5) 100%)"
        border_color = "#6B7280"
        badge_color = "#6B7280"
        text_desc = "สัญญาณรอเลือกทาง (Neutral): สัญญาณทางเทคนิคขัดแย้งกัน แนะนำถือครองเงินสดรอความชัดเจน"

    # Style warning box dynamically
    if "⚠️" in warning or "⚡" in warning:
        warning_html = f'<div class="strategy-warning">{warning}</div>'
    else:
        warning_html = f'<div class="strategy-warning" style="border-color: #34D399; color: #34D399; background-color: rgba(52, 211, 153, 0.05);">🟢 {warning}</div>'

    html_code = f"""
    <style>
    .strategy-card {{
        background: {bg_color};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 24px;
        margin: 20px 0;
        font-family: 'Inter', sans-serif;
    }}
    .strategy-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
    }}
    .strategy-badge {{
        background-color: {badge_color};
        color: #0E1117;
        font-weight: 800;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
    }}
    .strategy-confidence {{
        color: #9CA3AF;
        font-size: 0.95rem;
    }}
    .strategy-desc {{
        color: #E5E7EB;
        font-size: 1.05rem;
        margin-bottom: 20px;
        font-weight: 500;
    }}
    .strategy-warning {{
        background-color: rgba(239, 68, 68, 0.08);
        border: 1px dashed #EF4444;
        color: #F87171;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 20px;
        font-size: 0.95rem;
        line-height: 1.5;
    }}
    .strategy-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
    }}
    .strategy-metric-box {{
        background-color: rgba(31, 41, 55, 0.5);
        border: 1px solid rgba(75, 85, 99, 0.3);
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }}
    .strategy-metric-box.sl {{
        border-color: rgba(239, 68, 68, 0.4);
    }}
    .strategy-metric-box.tp {{
        border-color: rgba(16, 185, 129, 0.4);
    }}
    .strategy-metric-title {{
        color: #9CA3AF;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 6px;
    }}
    .strategy-metric-value {{
        font-size: 1.4rem;
        font-weight: 700;
        color: #F9FAFB;
    }}
    </style>
    
    <div class="strategy-card">
        <div class="strategy-header">
            <div>
                <span class="strategy-badge">{decision}</span>
            </div>
            <div class="strategy-confidence">
                Confidence / ความมั่นใจ: <strong>{confidence}%</strong>
            </div>
        </div>
        <div class="strategy-desc">
            {text_desc}
        </div>
        {warning_html}
        <div class="strategy-grid">
            <div class="strategy-metric-box">
                <div class="strategy-metric-title">🛒 Entry Price / จุดเข้าซื้อ</div>
                <div class="strategy-metric-value">${entry:,.2f}</div>
            </div>
            <div class="strategy-metric-box sl">
                <div class="strategy-metric-title" style="color: #F87171;">🛡️ Stop Loss (SL)</div>
                <div class="strategy-metric-value" style="color: #F87171;">${sl:,.2f}</div>
            </div>
            <div class="strategy-metric-box tp">
                <div class="strategy-metric-title" style="color: #34D399;">🎯 Take Profit 1 (TP1)</div>
                <div class="strategy-metric-value" style="color: #34D399;">${tp1:,.2f}</div>
            </div>
            <div class="strategy-metric-box tp">
                <div class="strategy-metric-title" style="color: #059669;">🎯 Take Profit 2 (TP2)</div>
                <div class="strategy-metric-value" style="color: #059669;">${tp2:,.2f}</div>
            </div>
        </div>
    </div>
    """
    clean_html = "\n".join([line.strip() for line in html_code.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)
