import streamlit as st
import pandas as pd
import numpy as np

def render_ttd_dashboard(ttd_data: dict):
    """
    Renders the Traders Trend Dashboard (TTD) table in Confluence Matrix style.
    """
    rows = []
    for tf, data in ttd_data.items():
        if not data:
            rows.append({
                "Timeframe": tf,
                "CDC Trend": "N/A",
                "CDC Signal": "N/A",
                "MACD Trend": "N/A",
                "Adaptive Trend": "N/A",
                "ADX": 20.0,
                "ADX Strength": "N/A",
                "BB Squeeze": False
            })
            continue
            
        rows.append({
            "Timeframe": tf,
            "CDC Trend": data.get("CDC_Trend", "Neutral"),
            "CDC Signal": data.get("CDC_Signal", "Hold"),
            "MACD Trend": data.get("MACD_Trend", "Neutral"),
            "Adaptive Trend": data.get("SuperTrend_Direction", data.get("Adaptive_Trend", "Neutral")),
            "ADX": data.get("ADX", 20.0),
            "ADX Strength": data.get("ADX_Strength", "Sideways"),
            "BB Squeeze": data.get("BB_Squeeze", False)
        })
        
    # Custom HTML styling for premium high-contrast Dark Terminal look
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
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        background-color: #111827;
        color: #F9FAFB;
        border: 1px solid #374151;
    }
    .ttd-table thead tr {
        background-color: #1F2937;
        color: #F9FAFB;
        text-align: left;
        font-weight: bold;
        border-bottom: 2px solid #374151;
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
        background-color: #1F2937;
    }
    .trend-bullish {
        color: #34D399;
        background-color: rgba(52, 211, 153, 0.2);
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .trend-bearish {
        color: #F87171;
        background-color: rgba(248, 113, 113, 0.2);
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .sig-buy {
        color: #34D399;
        border: 1px solid #34D399;
        background-color: rgba(52, 211, 153, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    .sig-sell {
        color: #F87171;
        border: 1px solid #F87171;
        background-color: rgba(248, 113, 113, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    .sig-hold {
        color: #9CA3AF;
        padding: 2px 6px;
    }
    .bb-squeeze {
        color: #FBBF24;
        background-color: rgba(251, 191, 36, 0.2);
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
        color: #F87171;
        font-weight: 700;
    }
    .adx-neutral {
        color: #D1D5DB;
    }
    </style>
    <table class="ttd-table">
        <thead>
            <tr>
                <th>Timeframe</th>
                <th>CDC Trend</th>
                <th>CDC Signal</th>
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
            
        adx_val = row.get("ADX", 20.0)
        adx_str = row.get("ADX Strength", "Sideways")
        if adx_str == "Strong Trend":
            adx_cls = "adx-strong"
        elif adx_str == "Sideways":
            adx_cls = "adx-weak"
        else:
            adx_cls = "adx-neutral"
            
        bb_squeeze = row.get("BB Squeeze", False)
        bb_text = "SQUEEZE ⚡" if bb_squeeze else "Normal"
        bb_cls = "bb-squeeze" if bb_squeeze else "bb-normal"
            
        html_code += f"""
            <tr>
                <td><strong>{row['Timeframe']}</strong></td>
                <td><span class="{cdc_trend_cls}">{row['CDC Trend']}</span></td>
                <td><span class="{sig_cls}">{row['CDC Signal']}</span></td>
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
    clean_html = "\n".join([line.strip() for line in html_code.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)

def render_trading_strategy_panel(strategy: dict):
    """
    Renders the upgraded premium Decision Card with high contrast (Regime & Volume Aware).
    """
    decision = strategy.get("Decision", "NEUTRAL")  # NO TRADE / WATCH / READY / ENTRY TRIGGERED / MANAGE TRADE
    alignment_type = strategy.get("AlignmentType", "CONFLICTED")
    direction = strategy.get("Direction", "NEUTRAL")
    confluence_score = strategy.get("ConfluenceScore", 0.0)
    directional_score = strategy.get("DirectionalScore", 0.0)
    quality_score = strategy.get("QualityScore", 0.0)
    
    entry = strategy.get("Entry", 0.0)
    sl = strategy.get("StopLoss", 0.0)
    tp1 = strategy.get("TakeProfit1", 0.0)
    tp2 = strategy.get("TakeProfit2", 0.0)
    rr_tp1 = strategy.get("RR_TP1", 0.0)
    rr_tp2 = strategy.get("RR_TP2", 0.0)
    
    reasons = strategy.get("Reasons", [])
    warnings = strategy.get("Warnings", [])
    vetoed = strategy.get("Vetoed", False)
    veto_reason = strategy.get("VetoReason", "")
    data_quality_warning = strategy.get("DataQualityWarning", False)

    # Sprint 4 additions
    regime = strategy.get("Regime", "UNKNOWN")
    regime_score = strategy.get("RegimeScore", 0.0)
    regime_flags = strategy.get("RegimeFlags", "")
    vol_conf = strategy.get("VolumeConfirmation", "NEUTRAL")
    vwap_align = strategy.get("VwapAlignment", "NEUTRAL")
    
    bos = strategy.get("BOS", 0)
    choch = strategy.get("CHOCH", 0)
    fvg = strategy.get("FVG", 0)
    liq = strategy.get("LiquiditySweep", 0)

    # Construct state titles and direction displays
    if decision == "ENTRY TRIGGERED":
        bg_color = "#064E3B"      # Solid Forest Green
        border_color = "#34D399"  # Bright Emerald
        badge_color = "#34D399"
        state_title = "💥 ENTRY TRIGGERED"
        direction_display = f"{direction} Direction"
    elif decision == "READY":
        bg_color = "#1E3A8A"      # Deep Royal Blue
        border_color = "#60A5FA"  # Bright Blue
        badge_color = "#60A5FA"
        state_title = "⚡ READY TO ENTER"
        direction_display = f"{direction} Direction"
    elif decision == "WATCH":
        bg_color = "#78350F"      # Dark Amber / Brown
        border_color = "#FBBF24"  # Gold
        badge_color = "#FBBF24"
        state_title = "👀 WATCH"
        direction_display = f"Technical Bias: {direction}"
    elif decision == "MANAGE TRADE":
        bg_color = "#4C1D95"      # Dark Purple
        border_color = "#A78BFA"  # Lavender
        badge_color = "#A78BFA"
        state_title = "🛡️ MANAGE ACTIVE TRADE"
        direction_display = f"{direction} Direction"
    else: # NO TRADE
        bg_color = "#1F2937"      # Solid Charcoal Grey
        border_color = "#4B5563"  # Cool Grey
        badge_color = "#9CA3AF"
        state_title = "🚫 NO TRADE"
        direction_display = f"Technical Bias: {direction}"

    # Alignment type badges
    align_color = "#38BDF8" if alignment_type == "TREND_FOLLOWING" else ("#F43F5E" if alignment_type == "COUNTER_TREND_SCALP" else "#9CA3AF")
    
    # Construct reasons and warnings HTML lists
    reasons_html = "".join([f"<li>✅ {r}</li>" for r in reasons])
    warnings_html = "".join([f"<li>⚠️ {w}</li>" for w in warnings])
    
    if vetoed:
        warnings_html += f'<li style="color: #FCA5A5; font-weight: 700;">❌ VETO: {veto_reason}</li>'
    if data_quality_warning:
        warnings_html += '<li style="color: #EF4444; font-weight: 800;">🛑 DATA QUALITY WARNING: History is too short for indicator warmups. Entry signals are locked.</li>'

    # Advanced SMC structure checklist
    smc_drivers = []
    if bos: smc_drivers.append("BOS 突破")
    if choch: smc_drivers.append("CHOCH 反转")
    if fvg: smc_drivers.append("FVG 失衡区")
    if liq: smc_drivers.append("Liquidity Sweep 扫损")
    smc_drivers_str = ", ".join(smc_drivers) if smc_drivers else "None"

    html_code = f"""
    <style>
    .decision-card {{
        background-color: {bg_color};
        border: 2px solid {border_color};
        border-radius: 12px;
        padding: 24px;
        margin: 20px 0;
        font-family: 'Inter', 'Outfit', sans-serif;
        color: #F9FAFB;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }}
    .decision-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-bottom: 1px solid rgba(255,255,255,0.15);
        padding-bottom: 15px;
    }}
    .decision-state-badge {{
        background-color: {badge_color};
        color: #111827;
        font-weight: 800;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 1.15rem;
        letter-spacing: 0.5px;
    }}
    .decision-align-badge {{
        border: 1px solid {align_color};
        color: {align_color};
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        text-transform: uppercase;
    }}
    .decision-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-bottom: 20px;
    }}
    .decision-metric-box {{
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }}
    .decision-metric-title {{
        color: #D1D5DB;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 6px;
        font-weight: 500;
    }}
    .decision-metric-value {{
        font-size: 1.45rem;
        font-weight: 800;
        color: #F9FAFB;
    }}
    .decision-rr-label {{
        font-size: 0.8rem;
        color: #9CA3AF;
        margin-top: 4px;
    }}
    .decision-details {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        border-top: 1px solid rgba(255,255,255,0.15);
        padding-top: 15px;
    }}
    .decision-list-title {{
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .decision-list {{
        list-style-type: none;
        padding-left: 0;
        margin: 0;
        font-size: 0.9rem;
        line-height: 1.5;
    }}
    .decision-list li {{
        margin-bottom: 6px;
    }}
    </style>
    
    <div class="decision-card">
        <div class="decision-header" style="flex-wrap: wrap; gap: 10px;">
            <div>
                <span class="decision-state-badge" title="Final Decision = ผลหลังผ่าน RR / Regime / Portfolio / Playbook filters">{state_title}</span>
                <span style="margin-left: 10px; font-weight: 700; font-size: 1.1rem; color: #F3F4F6;" title="Technical Bias = ทิศทางเชิงเทคนิค">
                    {direction_display}
                </span>
                <div style="font-size: 0.75rem; color: #9CA3AF; margin-top: 4px; margin-left: 5px;">
                    💡 <em>Technical Bias = ทิศทางเชิงเทคนิค | Final Decision = ผลหลังผ่าน RR / Regime / Portfolio / Playbook filters</em>
                </div>
            </div>
            <div>
                <span class="decision-align-badge">{alignment_type}</span>
            </div>
        </div>
        
        <div class="decision-grid">
            <div class="decision-metric-box">
                <div class="decision-metric-title">📊 Confluence Score</div>
                <div class="decision-metric-value">{confluence_score:.1f}%</div>
                <div class="decision-rr-label">Dir: {directional_score:+.0f} | Qual: {quality_score:.0f}</div>
            </div>
            <div class="decision-metric-box">
                <div class="decision-metric-title">🛒 Entry Zone</div>
                <div class="decision-metric-value">${entry:,.2f}</div>
                <div class="decision-rr-label">Current Market Price</div>
            </div>
            <div class="decision-metric-box" style="border-color: #F87171;">
                <div class="decision-metric-title" style="color: #FCA5A5;">🛡️ Stop Loss (SL)</div>
                <div class="decision-metric-value" style="color: #FCA5A5;">${sl:,.2f}</div>
                <div class="decision-rr-label">Structural / Volatility</div>
            </div>
            <div class="decision-metric-box" style="border-color: #34D399;">
                <div class="decision-metric-title" style="color: #A7F3D0;">🎯 TP Targets</div>
                <div class="decision-metric-value" style="color: #A7F3D0; font-size: 1.1rem; text-align: left; display: flex; flex-direction: column; gap: 2px;">
                    <div>TP1: ${tp1:,.2f} (RR: {rr_tp1:.2f})</div>
                    <div>TP2: ${tp2:,.2f} (RR: {rr_tp2:.2f})</div>
                </div>
            </div>
        </div>
        
        <!-- Sprint 4 Intelligence Section -->
        <div class="decision-grid" style="grid-template-columns: repeat(3, 1fr); margin-top: 10px; margin-bottom: 20px;">
            <div class="decision-metric-box" style="border-color: #A78BFA;">
                <div class="decision-metric-title" style="color: #C084FC;">⚙️ Market Regime</div>
                <div class="decision-metric-value" style="color: #C084FC; font-size: 1.25rem;">{regime} ({regime_score:.0f}%)</div>
                <div class="decision-rr-label">Flags: {regime_flags if regime_flags else "None"}</div>
            </div>
            <div class="decision-metric-box" style="border-color: #60A5FA;">
                <div class="decision-metric-title" style="color: #93C5FD;">🌊 Volume & VWAP</div>
                <div class="decision-metric-value" style="color: #93C5FD; font-size: 1.25rem;">{vol_conf} / {vwap_align}</div>
                <div class="decision-rr-label">Flow / VWAP Alignment</div>
            </div>
            <div class="decision-metric-box" style="border-color: #FBBF24;">
                <div class="decision-metric-title" style="color: #FDE047;">🗺️ Advanced SMC Drivers</div>
                <div class="decision-metric-value" style="color: #FDE047; font-size: 1.15rem;">{smc_drivers_str}</div>
                <div class="decision-rr-label">BOS/CHOCH/FVG/Sweep</div>
            </div>
        </div>
        
        <div class="decision-details">
            <div>
                <div class="decision-list-title" style="color: #34D399;">🟢 Confluence Drivers</div>
                <ul class="decision-list">
                    {reasons_html if reasons_html else "<li>No positive confluence factors active</li>"}
                </ul>
            </div>
            <div>
                <div class="decision-list-title" style="color: #F87171;">🔴 Risk Warnings & Vetoes</div>
                <ul class="decision-list">
                    {warnings_html if warnings_html else "<li>No active risk warnings</li>"}
                </ul>
            </div>
        </div>
    </div>
    """
    clean_html = "\n".join([line.strip() for line in html_code.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)

def render_top_metrics_bar(
    price: float, 
    price_change_pct: float, 
    trend: str, 
    sm_val: float, 
    support: float, 
    resistance: float
):
    """
    Renders a custom horizontal high-contrast metrics bar at the top of the dashboard.
    Prevents standard st.metric text truncation and improves visual design.
    """
    change_color = "#34D399" if price_change_pct >= 0 else "#F87171"
    change_sign = "+" if price_change_pct >= 0 else ""
    
    trend_color = "#34D399" if trend == "Bullish" else ("#F87171" if trend == "Bearish" else "#9CA3AF")
    trend_bg = "rgba(52, 211, 153, 0.15)" if trend == "Bullish" else ("rgba(248, 113, 113, 0.15)" if trend == "Bearish" else "rgba(156, 163, 175, 0.15)")
    
    html_code = f"""
    <style>
    .metrics-container {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 15px;
        margin-bottom: 25px;
        width: 100%;
    }}
    .metric-card {{
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        font-family: 'Inter', sans-serif;
    }}
    .metric-card-title {{
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #9CA3AF;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
        font-weight: 500;
    }}
    .metric-card-value {{
        font-size: 1.55rem;
        font-weight: 800;
        color: #F9FAFB;
        display: flex;
        align-items: baseline;
        gap: 8px;
    }}
    .metric-card-sub {{
        font-size: 0.85rem;
        font-weight: 600;
    }}
    </style>
    
    <div class="metrics-container">
        <div class="metric-card">
            <div class="metric-card-title">💵 Latest Price</div>
            <div class="metric-card-value">
                ${price:,.2f}
                <span class="metric-card-sub" style="color: {change_color};">{change_sign}{price_change_pct:.2f}% (15m)</span>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-card-title">📈 CDC Trend (15m)</div>
            <div class="metric-card-value">
                <span style="color: {trend_color}; background-color: {trend_bg}; padding: 2px 8px; border-radius: 4px; font-size: 1.25rem; font-weight: 700;">
                    {trend}
                </span>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-card-title">🏦 MCDX Smart Money</div>
            <div class="metric-card-value">
                {sm_val:.1f}%
                <span class="metric-card-sub" style="color: {'#34D399' if sm_val > 20 else '#9CA3AF'};">
                    {'(Bankers Active)' if sm_val > 20 else '(Low volume)'}
                </span>
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-card-title">🛡️ SMC S/R Zones</div>
            <div class="metric-card-value" style="font-size: 1.2rem; flex-direction: column; gap: 2px; align-items: flex-start;">
                <div style="color: #34D399; font-weight: 700;">🟢 S: ${support:,.2f}</div>
                <div style="color: #F87171; font-weight: 700;">🔴 R: ${resistance:,.2f}</div>
            </div>
        </div>
    </div>
    """
    clean_html = "\n".join([line.strip() for line in html_code.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)

def render_backtest_metrics_panel(metrics: dict):
    """
    Renders backtest performance summary metrics in a premium grid layout.
    """
    win_rate = metrics.get("win_rate", 0.0)
    profit_factor = metrics.get("profit_factor", 0.0)
    expectancy = metrics.get("expectancy", 0.0)
    max_dd = metrics.get("max_drawdown", 0.0)
    total_trades = metrics.get("total_trades", 0)
    total_signals = metrics.get("total_signals", 0)
    avg_holding = metrics.get("average_holding_bars", 0.0)
    consec_losses = metrics.get("max_consecutive_losses", 0)
    
    pf_str = f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞"
    
    html_code = f"""
    <style>
    .backtest-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-bottom: 25px;
    }}
    .backtest-card {{
        background-color: #1F2937;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 18px;
        text-align: center;
    }}
    .backtest-card-title {{
        color: #9CA3AF;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
    }}
    .backtest-card-value {{
        font-size: 1.6rem;
        font-weight: 800;
        color: #F9FAFB;
    }}
    </style>
    <div class="backtest-grid">
        <div class="backtest-card" style="border-color: #60A5FA;">
            <div class="backtest-card-title">📊 Win Rate</div>
            <div class="backtest-card-value" style="color: #60A5FA;">{win_rate:.1f}%</div>
        </div>
        <div class="backtest-card" style="border-color: #34D399;">
            <div class="backtest-card-title">📈 Profit Factor</div>
            <div class="backtest-card-value" style="color: #34D399;">{pf_str}</div>
        </div>
        <div class="backtest-card" style="border-color: #A78BFA;">
            <div class="backtest-card-title">🎯 Expectancy</div>
            <div class="backtest-card-value" style="color: #A78BFA;">{expectancy:+.2f} R</div>
        </div>
        <div class="backtest-card" style="border-color: #F87171;">
            <div class="backtest-card-title">📉 Max Drawdown</div>
            <div class="backtest-card-value" style="color: #F87171;">-{max_dd:.1f}%</div>
        </div>
    </div>
    
    <div class="backtest-grid">
        <div class="backtest-card">
            <div class="backtest-card-title">Signals / Trades</div>
            <div class="backtest-card-value">{total_signals} / {total_trades}</div>
        </div>
        <div class="backtest-card">
            <div class="backtest-card-title">Avg Holding Bars</div>
            <div class="backtest-card-value">{avg_holding:.1f}</div>
        </div>
        <div class="backtest-card">
            <div class="backtest-card-title">Consecutive Losses</div>
            <div class="backtest-card-value" style="color: #EF4444;">{consec_losses}</div>
        </div>
        <div class="backtest-card">
            <div class="backtest-card-title">TP1 / TP2 / SL Rates</div>
            <div class="backtest-card-value" style="font-size: 1.15rem; margin-top: 5px;">
                TP1: {metrics.get('tp1_rate', 0.0):.1f}% | TP2: {metrics.get('tp2_rate', 0.0):.1f}% | SL: {metrics.get('sl_rate', 0.0):.1f}%
            </div>
        </div>
    </div>
    """
    clean_html = "\n".join([line.strip() for line in html_code.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)
    
    if total_trades < 30:
        st.warning("⚠️ **Sample Size Warning:** Backtest has fewer than 30 trades. Metrics may not be statistically significant.")

def render_breakdown_tables(signals_data: list):
    """
    Computes and displays breakdown statistics for the backtest runs.
    """
    import pandas as pd
    if not signals_data:
        return
        
    df = pd.DataFrame(signals_data)
    
    st.markdown("### 🔍 Performance Breakdown")
    
    # 1. Alignment Type Breakdown
    if "alignment_type" in df.columns:
        st.write("**Breakdown by Alignment Type**")
        align_grp = df.groupby("alignment_type").agg(
            Trades=("realized_r_multiple", "count"),
            Avg_R=("realized_r_multiple", "mean"),
            Total_R=("realized_r_multiple", "sum")
        )
        st.dataframe(align_grp, use_container_width=True)
        
    # 2. Confluence Score Buckets
    if "confluence_score" in df.columns:
        st.write("**Breakdown by Confluence Score Range**")
        bins = [0, 50, 60, 70, 80, 90, 101]
        labels = ["<50%", "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"]
        df["score_bucket"] = pd.cut(df["confluence_score"], bins=bins, labels=labels)
        score_grp = df.groupby("score_bucket", observed=False).agg(
            Trades=("realized_r_multiple", "count"),
            Avg_R=("realized_r_multiple", "mean"),
            Total_R=("realized_r_multiple", "sum")
        )
        st.dataframe(score_grp, use_container_width=True)
        
    # 3. SMC Source Quality
    if "smc_support_source" in df.columns:
        st.write("**Breakdown by SMC Support Source**")
        smc_grp = df.groupby("smc_support_source").agg(
            Trades=("realized_r_multiple", "count"),
            Avg_R=("realized_r_multiple", "mean"),
            Total_R=("realized_r_multiple", "sum")
        )
        st.dataframe(smc_grp, use_container_width=True)

def render_recommendation_card(rec: dict):
    """
    Renders the walk-forward parameter calibration recommendations card.
    """
    import json
    params = json.loads(rec["params_json"]) if isinstance(rec["params_json"], str) else rec["params_json"]
    status = rec.get("recommendation_status", "UNKNOWN")
    score = rec.get("robustness_score", 0.0)
    samples = rec.get("sample_size", 0)
    notes = rec.get("notes", "")
    
    if status == "RECOMMENDED":
        badge_cls = "badge-rec-success"
        badge_title = "🌟 RECOMMENDED"
    elif "WARNING" in status:
        badge_cls = "badge-rec-warning"
        badge_title = f"⚠️ {status}"
    else:
        badge_cls = "badge-rec-rejected"
        badge_title = f"🚫 {status}"
        
    html = f"""
    <style>
    .rec-card {{
        background-color: #1F2937;
        border: 2px solid #374151;
        border-radius: 10px;
        padding: 20px;
        color: #F9FAFB;
        font-family: 'Inter', sans-serif;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        margin-bottom: 20px;
    }}
    .rec-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 12px;
        margin-bottom: 15px;
    }}
    .badge-rec-success {{
        background-color: #064E3B;
        color: #34D399;
        border: 1px solid #34D399;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
    }}
    .badge-rec-warning {{
        background-color: #78350F;
        color: #FBBF24;
        border: 1px solid #FBBF24;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
    }}
    .badge-rec-rejected {{
        background-color: #991B1B;
        color: #FCA5A5;
        border: 1px solid #FCA5A5;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
    }}
    .rec-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-bottom: 15px;
    }}
    .rec-param-box {{
        background-color: #111827;
        border: 1px solid #374151;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
    }}
    .rec-param-title {{
        color: #9CA3AF;
        font-size: 0.75rem;
        text-transform: uppercase;
        margin-bottom: 4px;
    }}
    .rec-param-value {{
        font-size: 1.15rem;
        font-weight: 700;
    }}
    </style>
    <div class="rec-card">
        <div class="rec-header">
            <div>
                <span class="{badge_cls}">{badge_title}</span>
                <span style="margin-left: 10px; font-weight: 700; font-size: 1rem; color: #E5E7EB;">
                    Robustness: {score:.1f}% | Out-of-Sample Trades: {samples}
                </span>
            </div>
            <div style="font-size: 0.8rem; color: #9CA3AF;">
                Valid From: {rec['valid_from'][:19]}
            </div>
        </div>
        <div class="rec-grid">
            <div class="rec-param-box">
                <div class="rec-param-title">Confluence Thresh</div>
                <div class="rec-param-value" style="color: #60A5FA;">{params.get('confluence_threshold', 70.0):.1f}%</div>
            </div>
            <div class="rec-param-box">
                <div class="rec-param-title">Min R/R Limit</div>
                <div class="rec-param-value" style="color: #34D399;">{params.get('rr_threshold', 1.5):.2f} R</div>
            </div>
            <div class="rec-param-box">
                <div class="rec-param-title">ADX Strength</div>
                <div class="rec-param-value" style="color: #FBBF24;">{params.get('adx_threshold', 25.0):.1f}</div>
            </div>
            <div class="rec-param-box">
                <div class="rec-param-title">Max Bars Hold</div>
                <div class="rec-param-value" style="color: #F43F5E;">{params.get('max_bars_to_hold', 24)}</div>
            </div>
        </div>
        <div style="font-size: 0.85rem; color: #9CA3AF; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 8px;">
            <strong>Notes / Validation Details:</strong> {notes}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_opt_results_table(results: list):
    """
    Renders walk-forward window index results as a clean high-contrast table.
    """
    import json
    if not results:
        st.info("No window results available.")
        return
        
    html = """
    <table style="width: 100%; border-collapse: collapse; background-color: #1F2937; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.3); font-family: 'Inter', sans-serif; color: #F9FAFB; font-size: 0.85rem;">
        <thead>
            <tr style="background-color: #111827; border-bottom: 2px solid #374151; text-align: left;">
                <th style="padding: 12px 15px;">Window</th>
                <th style="padding: 12px 15px;">OOS Test Period</th>
                <th style="padding: 12px 15px;">Optimal Params</th>
                <th style="padding: 12px 15px; text-align: center;">In-Sample Exp</th>
                <th style="padding: 12px 15px; text-align: center;">Out-Sample Exp</th>
                <th style="padding: 12px 15px; text-align: center;">Robustness</th>
                <th style="padding: 12px 15px;">Warnings</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for r in results:
        params = json.loads(r["params_json"]) if isinstance(r["params_json"], str) else r["params_json"]
        is_metrics = json.loads(r["in_sample_metrics_json"]) if isinstance(r["in_sample_metrics_json"], str) else r["in_sample_metrics_json"]
        oos_metrics = json.loads(r["out_sample_metrics_json"]) if isinstance(r["out_sample_metrics_json"], str) else r["out_sample_metrics_json"]
        warnings = json.loads(r["warnings_json"]) if isinstance(r["warnings_json"], str) else r["warnings_json"]
        
        warns_str = ", ".join(warnings) if warnings else "-"
        warn_style = "color: #FCA5A5;" if warnings else "color: #9CA3AF;"
        
        param_desc = f"Conf: {params.get('confluence_threshold', 70.0):.0f}%, RR: {params.get('rr_threshold', 1.5):.1f}"
        
        html += f"""
            <tr style="border-bottom: 1px solid #374151;">
                <td style="padding: 10px 15px; font-weight: 700;">#{r['window_index']}</td>
                <td style="padding: 10px 15px; color: #E5E7EB;">{r['test_start'][:10]} to {r['test_end'][:10]}</td>
                <td style="padding: 10px 15px; color: #60A5FA;">{param_desc}</td>
                <td style="padding: 10px 15px; text-align: center; color: #34D399;">{is_metrics.get('expectancy', 0.0):+.2f}R ({is_metrics.get('total_trades', 0)} t)</td>
                <td style="padding: 10px 15px; text-align: center; color: #10B981; font-weight: 700;">{oos_metrics.get('expectancy', 0.0):+.2f}R ({oos_metrics.get('total_trades', 0)} t)</td>
                <td style="padding: 10px 15px; text-align: center; font-weight: 700; color: #FBBF24;">{r['robustness_score']:.1f}%</td>
                <td style="padding: 10px 15px; {warn_style}">{warns_str}</td>
            </tr>
        """
        
    html += """
        </tbody>
    </table>
    """
    
    clean_html = "\n".join([line.strip() for line in html.split("\n")])
    st.markdown(clean_html, unsafe_allow_html=True)


