import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def draw_advanced_charts(
    df: pd.DataFrame, 
    ticker: str, 
    timeframe: str = None, 
    strategy: dict = None,
    show_vwap: bool = False,
    show_fvg: bool = False,
    show_ob: bool = False,
    show_sweeps: bool = False,
    show_bos_choch: bool = False,
    show_eql_eqh: bool = False,
    show_market_regime_shading: bool = False,
    show_equal_highs_lows: bool = None,
    show_regime: bool = None,
    tf: str = None
):
    if not timeframe and tf:
        timeframe = tf
        
    if show_equal_highs_lows is not None:
        show_eql_eqh = show_equal_highs_lows
        
    if show_regime is not None:
        show_market_regime_shading = show_regime
    """
    Draws a Plotly figure with 4 subplots:
    1. Candlestick chart + EMAs + KAMA + Confirmed SMC Support/Resistance levels + Bollinger Bands + optional overlays
    2. MACD (Line, Signal, Histogram)
    3. Custom MCDX Proxy oscillator
    4. Classic MCDX smart money flows (Stacked Bankers/Speculators/Retailers)
    """
    if df.empty:
        st.warning("No data to display in chart.")
        return
        
    df = df.copy()
    
    # Keep last 150 bars for high-definition rendering
    plot_df = df.tail(150)
    
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=(
            f"{ticker} - {timeframe} | Price, indicators & Confirmed SMC Levels",
            "MACD (12, 26, 9)",
            "MCDX Proxy (RSI 14 * ATR 14) Momentum Strength",
            "MCDX Smart Money Flow (%)"
        )
    )
    
    # ------------------ Row 1: Candlestick & Overlays ------------------
    # Bollinger Bands
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
            
    # Candlestick
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
    
    # EMAs
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
        
    # KAMA
    if "KAMA" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["KAMA"], name="KAMA", line=dict(color="#C084FC", width=1, dash="dash")),
            row=1, col=1
        )
        
    # VWAP Overlay
    if show_vwap and "VWAP" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["VWAP"], name="VWAP", line=dict(color="#06B6D4", width=1.5, dash="dashdot")),
            row=1, col=1
        )
        
    # Confirmed SMC S/R Zones (No-Repaint)
    if "Support_Level" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["Support_Level"], name="SMC Confirmed Support", line=dict(color="#059669", width=1.5, dash="dot")),
            row=1, col=1
        )
    if "Resistance_Level" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["Resistance_Level"], name="SMC Confirmed Resistance", line=dict(color="#DC2626", width=1.5, dash="dot")),
            row=1, col=1
        )
        
    # Target levels from decision engine
    if strategy is not None:
        entry = strategy.get("Entry", 0.0)
        sl = strategy.get("StopLoss", 0.0)
        tp1 = strategy.get("TakeProfit1", 0.0)
        tp2 = strategy.get("TakeProfit2", 0.0)
        dec = strategy.get("Decision", "NEUTRAL")
        
        if dec != "NEUTRAL":
            if entry > 0:
                fig.add_trace(
                    go.Scatter(x=plot_df.index, y=[entry]*len(plot_df), name="Entry Zone", line=dict(color="#3B82F6", width=1.5, dash="dash")),
                    row=1, col=1
                )
            if sl > 0:
                fig.add_trace(
                    go.Scatter(x=plot_df.index, y=[sl]*len(plot_df), name="Stop Loss", line=dict(color="#EF4444", width=1.5, dash="dash")),
                    row=1, col=1
                )
            if tp1 > 0:
                fig.add_trace(
                    go.Scatter(x=plot_df.index, y=[tp1]*len(plot_df), name="TP1", line=dict(color="#10B981", width=1.5, dash="dash")),
                    row=1, col=1
                )
            if tp2 > 0:
                fig.add_trace(
                    go.Scatter(x=plot_df.index, y=[tp2]*len(plot_df), name="TP2", line=dict(color="#059669", width=1.5, dash="dash")),
                    row=1, col=1
                )
        
    # Historical Swing Point Markers
    if "Swing_High" in plot_df.columns:
        swing_highs = plot_df[plot_df["Swing_High"].notna()]
        if not swing_highs.empty:
            fig.add_trace(
                go.Scatter(
                    x=swing_highs.index, y=swing_highs["Swing_High"],
                    mode="markers",
                    marker=dict(symbol="triangle-down", size=8, color="#EF4444"),
                    name="Swing High Peak"
                ),
                row=1, col=1
            )
        
    if "Swing_Low" in plot_df.columns:
        swing_lows = plot_df[plot_df["Swing_Low"].notna()]
        if not swing_lows.empty:
            fig.add_trace(
                go.Scatter(
                    x=swing_lows.index, y=swing_lows["Swing_Low"],
                    mode="markers",
                    marker=dict(symbol="triangle-up", size=8, color="#10B981"),
                name="Swing Low Valley"
            ),
            row=1, col=1
        )
        
    # BOS / CHOCH Markers
    if show_bos_choch:
        if "BOS_Present" in plot_df.columns:
            bos_rows = plot_df[plot_df["BOS_Present"] == 1]
            if not bos_rows.empty:
                fig.add_trace(
                    go.Scatter(
                        x=bos_rows.index, y=bos_rows["Close"],
                        mode="markers+text",
                        text=["BOS"] * len(bos_rows),
                        textposition="top center",
                        marker=dict(symbol="star", size=10, color="#FBBF24"),
                        name="BOS (Break of Structure)"
                    ),
                    row=1, col=1
                )
        if "CHOCH_Present" in plot_df.columns:
            choch_rows = plot_df[plot_df["CHOCH_Present"] == 1]
            if not choch_rows.empty:
                fig.add_trace(
                    go.Scatter(
                        x=choch_rows.index, y=choch_rows["Close"],
                        mode="markers+text",
                        text=["CHOCH"] * len(choch_rows),
                        textposition="top center",
                        marker=dict(symbol="diamond", size=10, color="#EC4899"),
                        name="CHOCH (Change of Character)"
                    ),
                    row=1, col=1
                )
                
    # Liquidity Sweeps Markers
    if show_sweeps and "Liquidity_Sweep" in plot_df.columns:
        sweep_rows = plot_df[plot_df["Liquidity_Sweep"] == 1]
        if not sweep_rows.empty:
            fig.add_trace(
                go.Scatter(
                    x=sweep_rows.index, y=np.where(sweep_rows["Sweep_Direction"] == "BULLISH", sweep_rows["Low"], sweep_rows["High"]),
                    mode="markers",
                    marker=dict(symbol="circle-open", size=12, color="#06B6D4", line=dict(width=2)),
                    name="Liquidity Sweep"
                ),
                row=1, col=1
            )
            
    # Equal Highs / Equal Lows Markers
    if show_eql_eqh:
        if "Equal_Highs" in plot_df.columns:
            eqh_rows = plot_df[plot_df["Equal_Highs"] == 1]
            if not eqh_rows.empty:
                fig.add_trace(
                    go.Scatter(
                        x=eqh_rows.index, y=eqh_rows["High"],
                        mode="markers+text",
                        text=["EQH"] * len(eqh_rows),
                        textposition="top center",
                        marker=dict(symbol="circle", size=8, color="#FCA5A5"),
                        name="Equal Highs (EQH)"
                    ),
                    row=1, col=1
                )
        if "Equal_Lows" in plot_df.columns:
            eql_rows = plot_df[plot_df["Equal_Lows"] == 1]
            if not eql_rows.empty:
                fig.add_trace(
                    go.Scatter(
                        x=eql_rows.index, y=eql_rows["Low"],
                        mode="markers+text",
                        text=["EQL"] * len(eql_rows),
                        textposition="bottom center",
                        marker=dict(symbol="circle", size=8, color="#86EFAC"),
                        name="Equal Lows (EQL)"
                    ),
                    row=1, col=1
                )
                
    # Generate background rectangle shapes for FVG and OB candidates
    shapes = []
    indices = plot_df.index
    
    if show_market_regime_shading and "primary_regime" in plot_df.columns:
        regimes = plot_df["primary_regime"].values
        n = len(plot_df)
        i = 0
        min_y = plot_df["Low"].min() * 0.999
        max_y = plot_df["High"].max() * 1.001
        while i < n:
            reg = regimes[i]
            start_time = indices[i]
            j = i
            while j < n and regimes[j] == reg:
                j += 1
            end_time = indices[j - 1]
            
            if reg == "TRENDING_UP":
                color = "rgba(16, 185, 129, 0.03)"
            elif reg == "TRENDING_DOWN":
                color = "rgba(239, 68, 68, 0.03)"
            elif reg == "SIDEWAYS":
                color = "rgba(156, 163, 175, 0.03)"
            else:
                color = "rgba(245, 158, 11, 0.03)"
                
            shapes.append(dict(
                type="rect",
                xref="x", yref="y",
                x0=start_time, x1=end_time,
                y0=min_y, y1=max_y,
                fillcolor=color,
                line=dict(width=0),
                layer="below"
            ))
            i = j
    
    if show_fvg and "FVG_Present" in plot_df.columns:
        for i in range(len(plot_df)):
            row = plot_df.iloc[i]
            if row["FVG_Present"] == 1:
                t_time = indices[i]
                t_minus_2_time = indices[max(0, i-2)]
                if row["FVG_Direction"] == "BULLISH":
                    y0 = plot_df["High"].iloc[max(0, i-2)]
                    y1 = plot_df["Low"].iloc[i]
                    color = "rgba(16, 185, 129, 0.2)"
                else:
                    y0 = plot_df["Low"].iloc[max(0, i-2)]
                    y1 = plot_df["High"].iloc[i]
                    color = "rgba(239, 68, 68, 0.2)"
                shapes.append(dict(
                    type="rect",
                    xref="x", yref="y",
                    x0=t_minus_2_time, x1=t_time,
                    y0=y0, y1=y1,
                    fillcolor=color,
                    line=dict(width=0),
                    layer="below"
                ))
                
    if show_ob and "OB_Candidate" in plot_df.columns:
        for i in range(len(plot_df)):
            row = plot_df.iloc[i]
            if row["OB_Candidate"] == 1:
                t_time = indices[i]
                color = "rgba(16, 185, 129, 0.25)" if row["OB_Direction"] == "BULLISH" else "rgba(239, 68, 68, 0.25)"
                shapes.append(dict(
                    type="rect",
                    xref="x", yref="y",
                    x0=t_time, x1=t_time,
                    y0=min(row["Open"], row["Close"]), y1=max(row["Open"], row["Close"]),
                    fillcolor=color,
                    line=dict(color=color, width=1),
                    layer="below"
                ))
                
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
        hist_colors = np.where(plot_df["MACD_Hist"] >= 0, "#10B981", "#EF4444")
        fig.add_trace(
            go.Bar(x=plot_df.index, y=plot_df["MACD_Hist"], name="Histogram", marker_color=hist_colors),
            row=2, col=1
        )
 
    # ------------------ Row 3: MCDX Proxy ------------------
    if "MCDX_Proxy" in plot_df.columns:
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["MCDX_Proxy"], name="MCDX Proxy Strength", line=dict(color="#F472B6", width=2)),
            row=3, col=1
        )
        
    # ------------------ Row 4: Classic MCDX Money Flow ------------------
    if "MCDX_Smart" in plot_df.columns:
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
        
    fig.update_layout(
        template="plotly_dark",
        height=850,
        margin=dict(l=50, r=30, t=50, b=50),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        shapes=shapes,
        plot_bgcolor="#111827",
        paper_bgcolor="#111827"
    )
    
    fig.update_xaxes(rangeslider_visible=False)
    fig.update_xaxes(showgrid=True, gridcolor="#374151", linecolor="#4B5563")
    fig.update_yaxes(showgrid=True, gridcolor="#374151", linecolor="#4B5563")
    
    st.plotly_chart(fig, use_container_width=True)
