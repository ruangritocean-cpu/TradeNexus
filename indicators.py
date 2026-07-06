import pandas as pd
import numpy as np
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

def calculate_cdc_actionzone(df: pd.DataFrame, fast_len: int = 12, slow_len: int = 26) -> pd.DataFrame:
    """
    Calculates the CDC ActionZone (Simplified).
    - Bullish Trend (Green): EMA(fast) > EMA(slow)
    - Bearish Trend (Red): EMA(fast) < EMA(slow)
    
    Adds columns:
    - 'EMA_Fast': Fast EMA
    - 'EMA_Slow': Slow EMA
    - 'CDC_Trend': 'Bullish' or 'Bearish'
    - 'CDC_Signal': 'Buy', 'Sell', or 'Hold'
    """
    if len(df) < max(fast_len, slow_len):
        logger.warning("Dataframe length too short for CDC calculation.")
        df["EMA_Fast"] = np.nan
        df["EMA_Slow"] = np.nan
        df["CDC_Trend"] = "Neutral"
        df["CDC_Signal"] = "Hold"
        return df

    df = df.copy()
    
    # Calculate EMAs using pandas ewm for numerical stability
    df["EMA_Fast"] = df["Close"].ewm(span=fast_len, adjust=False).mean()
    df["EMA_Slow"] = df["Close"].ewm(span=slow_len, adjust=False).mean()
    
    # Determine Trend
    df["CDC_Trend"] = np.where(df["EMA_Fast"] > df["EMA_Slow"], "Bullish", "Bearish")
    
    # Signal Crossovers
    # Shift trend to identify state changes
    prev_trend = df["CDC_Trend"].shift(1)
    
    df["CDC_Signal"] = "Hold"
    df.loc[(df["CDC_Trend"] == "Bullish") & (prev_trend == "Bearish"), "CDC_Signal"] = "Buy"
    df.loc[(df["CDC_Trend"] == "Bearish") & (prev_trend == "Bullish"), "CDC_Signal"] = "Sell"
    
    return df

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculates MACD (12, 26, 9) and adds:
    - 'MACD': MACD line
    - 'MACD_Signal': Signal line
    - 'MACD_Hist': Histogram
    - 'MACD_Trend': 'Bullish' or 'Bearish' crossover
    """
    if len(df) < max(fast, slow) + signal:
        df["MACD"] = np.nan
        df["MACD_Signal"] = np.nan
        df["MACD_Hist"] = np.nan
        df["MACD_Trend"] = "Neutral"
        return df
        
    df = df.copy()
    
    # Calculate MACD
    macd_df = ta.macd(df["Close"], fast=fast, slow=slow, signal=signal)
    if macd_df is not None and not macd_df.empty:
        df["MACD"] = macd_df.iloc[:, 0]       # MACD Line
        df["MACD_Hist"] = macd_df.iloc[:, 1]  # Histogram
        df["MACD_Signal"] = macd_df.iloc[:, 2] # Signal Line
    else:
        # Fallback to pandas ewm
        fast_ema = df["Close"].ewm(span=fast, adjust=False).mean()
        slow_ema = df["Close"].ewm(span=slow, adjust=False).mean()
        df["MACD"] = fast_ema - slow_ema
        df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
        df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
        
    # MACD Trend classification
    df["MACD_Trend"] = np.where(df["MACD"] > df["MACD_Signal"], "Bullish", "Bearish")
    
    # Signal Crossovers
    prev_macd_trend = df["MACD_Trend"].shift(1)
    df["MACD_Crossover"] = "None"
    df.loc[(df["MACD_Trend"] == "Bullish") & (prev_macd_trend == "Bearish"), "MACD_Crossover"] = "Bullish Crossover"
    df.loc[(df["MACD_Trend"] == "Bearish") & (prev_macd_trend == "Bullish"), "MACD_Crossover"] = "Bearish Crossover"
    
    return df

def calculate_smc_lite(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """
    SMC Lite: Identifies swing highs and swing lows over a rolling window.
    A swing high is the peak in a rolling window of 2 * k + 1, centered.
    For a 20-period rolling window, we use k = 10 (total 21 periods).
    
    Adds columns:
    - 'Swing_High': Value of swing high if found, else NaN
    - 'Swing_Low': Value of swing low if found, else NaN
    - 'Support_Level': Level of recent confirmed swing low
    - 'Resistance_Level': Level of recent confirmed swing high
    """
    df = df.copy()
    df["Swing_High"] = np.nan
    df["Swing_Low"] = np.nan
    
    k = window // 2  # default 10 for window = 20
    
    if len(df) < window:
        df["Support_Level"] = np.nan
        df["Resistance_Level"] = np.nan
        return df

    # Find local maxima/minima in centered window
    high_vals = df["High"].values
    low_vals = df["Low"].values
    
    for i in range(k, len(df) - k):
        # Swing High
        center_high = high_vals[i]
        is_high = True
        for j in range(i - k, i + k + 1):
            if high_vals[j] > center_high:
                is_high = False
                break
        if is_high:
            df.iloc[i, df.columns.get_loc("Swing_High")] = center_high
            
        # Swing Low
        center_low = low_vals[i]
        is_low = True
        for j in range(i - k, i + k + 1):
            if low_vals[j] < center_low:
                is_low = False
                break
        if is_low:
            df.iloc[i, df.columns.get_loc("Swing_Low")] = center_low
            
    # Forward fill support and resistance levels from detected swings
    df["Support_Level"] = df["Swing_Low"].ffill()
    df["Resistance_Level"] = df["Swing_High"].ffill()
    
    # Fill initial NaNs with the first available levels or price extremes
    df["Support_Level"] = df["Support_Level"].fillna(df["Low"].cummin())
    df["Resistance_Level"] = df["Resistance_Level"].fillna(df["High"].cummax())
    
    return df

def calculate_mcdx_proxy(df: pd.DataFrame, rsi_len: int = 14, atr_len: int = 14) -> pd.DataFrame:
    """
    MCDX (Proxy): Calculate RSI (14) and multiply by volatility factor (ATR 14)
    to create a custom momentum strength oscillator.
    
    Also provides a classic MCDX "Smart Money Flow" calculation:
    - Retailer (Green): Base RSI levels representing low volume/retail
    - Hot Money (Yellow): Mid RSI levels representing hot money
    - Smart Money (Red): Banker/Smart money based on high RSI levels smoothed
    """
    if len(df) < max(rsi_len, atr_len):
        df["RSI"] = 50.0
        df["ATR"] = 0.0
        df["MCDX_Proxy"] = 0.0
        df["MCDX_Smart"] = 0.0
        df["MCDX_Hot"] = 0.0
        df["MCDX_Retail"] = 100.0
        return df

    df = df.copy()
    
    # Calculate RSI
    df["RSI"] = ta.rsi(df["Close"], length=rsi_len)
    df["RSI"] = df["RSI"].fillna(50.0)
    
    # Calculate ATR
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], length=atr_len)
    df["ATR"] = df["ATR"].bfill().fillna(0.0)
    
    # Custom Proxy: RSI * ATR
    df["MCDX_Proxy"] = df["RSI"] * df["ATR"]
    
    # Classic MCDX logic (Banker, Hot Money, Retailer)
    # Scale RSI to mimic the typical 3-tier distribution
    # Banker (Smart Money - Red): active when RSI is high
    # Hot Money (Yellow): active when RSI is mid-to-high
    # Retailer (Green): active when RSI is low
    
    # Mathematical approximation:
    # banker_val = 1.5 * (RSI - 50)
    # banker_val is bounded by 0 and 20, then smoothed
    rsi_scaled = (df["RSI"] - 30) / (70 - 30) * 100  # Map 30-70 RSI to 0-100
    rsi_scaled = np.clip(rsi_scaled, 0, 100)
    
    # Banker (Smart Money - Red): high volume, strong uptrend
    df["MCDX_Smart"] = np.where(rsi_scaled > 50, (rsi_scaled - 50) * 2, 0)
    # Smooth smart money
    df["MCDX_Smart"] = df["MCDX_Smart"].ewm(span=5, adjust=False).mean()
    
    # Retailer (Green): dominant when trend is weak or downward
    df["MCDX_Retail"] = np.where(rsi_scaled < 50, (50 - rsi_scaled) * 2, 0)
    df["MCDX_Retail"] = df["MCDX_Retail"].ewm(span=5, adjust=False).mean()
    
    # Hot Money (Yellow): mid-level trend presence
    df["MCDX_Hot"] = 100 - df["MCDX_Smart"] - df["MCDX_Retail"]
    df["MCDX_Hot"] = np.clip(df["MCDX_Hot"], 0, 100)
    
    # Re-normalize to ensure they sum to 100%
    total = df["MCDX_Smart"] + df["MCDX_Hot"] + df["MCDX_Retail"]
    df["MCDX_Smart"] = (df["MCDX_Smart"] / total) * 100
    df["MCDX_Hot"] = (df["MCDX_Hot"] / total) * 100
    df["MCDX_Retail"] = (df["MCDX_Retail"] / total) * 100
    
    return df

def calculate_adaptive_trend(df: pd.DataFrame, period: int = 10, fast: int = 2, slow: int = 30) -> pd.DataFrame:
    """
    Adaptive Trend Finder using Kaufman's Adaptive Moving Average (KAMA)
    and ATR-based Adaptive Bands (similar to SuperTrend).
    
    Adds columns:
    - 'KAMA': Kaufman's Adaptive Moving Average
    - 'Adaptive_Trend': 'Bullish' or 'Bearish'
    """
    df = df.copy()
    if len(df) < period + 2:
        df["KAMA"] = df["Close"]
        df["Adaptive_Trend"] = "Neutral"
        return df
        
    close = df["Close"].values
    kama = np.zeros(len(df))
    kama[period - 1] = close[period - 1]  # Initialize first KAMA as close
    
    # Pre-calculate Efficiency Ratio components
    direction = np.abs(df["Close"] - df["Close"].shift(period))
    volatility = np.abs(df["Close"] - df["Close"].shift(1)).rolling(window=period).sum()
    
    er = np.zeros(len(df))
    # Safe division
    with np.errstate(divide='ignore', invalid='ignore'):
        er = np.where(volatility > 0, direction / volatility, 0)
    
    fast_sc = 2.0 / (fast + 1)
    slow_sc = 2.0 / (slow + 1)
    
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
    
    for i in range(period, len(df)):
        kama[i] = kama[i-1] + sc[i] * (close[i] - kama[i-1])
        
    df["KAMA"] = kama
    # Replace initial zeros (before calculations start) with close
    df.loc[df["KAMA"] == 0, "KAMA"] = df["Close"]
    
    # Adaptive Trend logic (Price relative to KAMA)
    # Bullish if close > KAMA, Bearish if close < KAMA
    df["Adaptive_Trend"] = np.where(df["Close"] > df["KAMA"], "Bullish", "Bearish")
    
    # Also calculate SuperTrend as an alternative adaptive trend finder
    # which is widely used and visually excellent
    try:
        st_df = ta.supertrend(df["High"], df["Low"], df["Close"], length=10, multiplier=3.0)
        if st_df is not None and not st_df.empty:
            df["SuperTrend"] = st_df.iloc[:, 0]  # SuperTrend Line
            df["SuperTrend_Direction"] = np.where(st_df.iloc[:, 1] > 0, "Bullish", "Bearish")  # Direction 1 or -1
        else:
            df["SuperTrend"] = df["KAMA"]
            df["SuperTrend_Direction"] = df["Adaptive_Trend"]
    except Exception as e:
        logger.warning(f"SuperTrend calculation failed: {str(e)}. Using KAMA as fallback.")
        df["SuperTrend"] = df["KAMA"]
        df["SuperTrend_Direction"] = df["Adaptive_Trend"]
        
    return df

def calculate_bollinger_bands(df: pd.DataFrame, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """
    Calculates Bollinger Bands and Squeeze Alert.
    Adds columns:
    - 'BBL': Lower Band
    - 'BBM': Middle Band (SMA 20)
    - 'BBU': Upper Band
    - 'BB_Bandwidth': Bandwidth percentage
    - 'BB_Squeeze': Boolean indicating if bands are in a squeeze
    """
    df = df.copy()
    if len(df) < length:
        df["BBL"] = np.nan
        df["BBM"] = np.nan
        df["BBU"] = np.nan
        df["BB_Bandwidth"] = np.nan
        df["BB_Squeeze"] = False
        return df

    bb_df = ta.bbands(df["Close"], length=length, std=std)
    if bb_df is not None and not bb_df.empty:
        df["BBL"] = bb_df.iloc[:, 0]
        df["BBM"] = bb_df.iloc[:, 1]
        df["BBU"] = bb_df.iloc[:, 2]
        df["BB_Bandwidth"] = bb_df.iloc[:, 3]
    else:
        # Fallback to rolling std
        df["BBM"] = df["Close"].rolling(window=length).mean()
        rolling_std = df["Close"].rolling(window=length).std()
        df["BBU"] = df["BBM"] + (std * rolling_std)
        df["BBL"] = df["BBM"] - (std * rolling_std)
        df["BB_Bandwidth"] = (df["BBU"] - df["BBL"]) / df["BBM"]

    # Calculate rolling minimum bandwidth over 100 periods
    bw = df["BB_Bandwidth"]
    if len(df) >= 100:
        bandwidth_quantile = bw.rolling(window=100).quantile(0.20)
        df["BB_Squeeze"] = bw < bandwidth_quantile
    else:
        df["BB_Squeeze"] = False
        
    df["BB_Squeeze"] = df["BB_Squeeze"].fillna(False)
    return df

def calculate_adx(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    """
    Calculates Average Directional Index (ADX) using pandas_ta.
    Adds columns:
    - 'ADX': Average Directional Index
    - 'ADX_Strength': 'Strong Trend', 'Weak Trend', or 'Sideways'
    """
    df = df.copy()
    if len(df) < 2 * length:
        df["ADX"] = np.nan
        df["ADX_Strength"] = "Sideways"
        return df

    adx_df = ta.adx(df["High"], df["Low"], df["Close"], length=length)
    if adx_df is not None and not adx_df.empty:
        df["ADX"] = adx_df.iloc[:, 0]
    else:
        df["ADX"] = np.nan
        
    df["ADX"] = df["ADX"].bfill().fillna(20.0)
    
    # Classify strength
    df["ADX_Strength"] = np.where(df["ADX"] >= 25, "Strong Trend", 
                                  np.where(df["ADX"] < 20, "Sideways", "Weak Trend"))
    return df

def generate_trading_signal(latest_data: dict) -> dict:
    """
    Generates trading decision, entry, TP, and SL levels based on technical indicators.
    Now incorporates ADX (Trend Strength) and Bollinger Bands (Squeeze Alerts).
    
    Args:
        latest_data (dict): Dictionary of the latest row metrics from the technical dataframe.
        
    Returns:
        dict: Decision details (Decision, Confidence, Entry, StopLoss, TakeProfit1, TakeProfit2, Risk, Warning)
    """
    price = latest_data.get("Close", 0.0)
    cdc_trend = latest_data.get("CDC_Trend", "Neutral")
    macd_trend = latest_data.get("MACD_Trend", "Neutral")
    supertrend_dir = latest_data.get("SuperTrend_Direction", "Neutral")
    support = latest_data.get("Support_Level", 0.0)
    resistance = latest_data.get("Resistance_Level", 0.0)
    atr = latest_data.get("ATR", 0.0)
    adx = latest_data.get("ADX", 20.0)
    bb_squeeze = latest_data.get("BB_Squeeze", False)
    
    # Core Decision Logic
    decision = "NEUTRAL"
    confidence = 50  # %
    
    if cdc_trend == "Bullish" and supertrend_dir == "Bullish":
        if macd_trend == "Bullish":
            decision = "STRONG BUY"
            confidence = 90
        else:
            decision = "BUY"
            confidence = 70
    elif cdc_trend == "Bearish" and supertrend_dir == "Bearish":
        if macd_trend == "Bearish":
            decision = "STRONG SELL"
            confidence = 90
        else:
            decision = "SELL"
            confidence = 70
    else:
        # Mixed signals
        if cdc_trend == "Bullish":
            decision = "BUY (RISKY)"
            confidence = 55
        elif cdc_trend == "Bearish":
            decision = "SELL (RISKY)"
            confidence = 55

    # Filter by ADX Trend Strength:
    # If the trend is very weak (sideways) and we have a signal, we reduce confidence
    # and mark it as risky to avoid whipsaws.
    if adx < 20 and decision != "NEUTRAL":
        confidence = max(confidence - 15, 40)
        
    # Build Warning messages
    warnings = []
    if adx < 20:
        warnings.append("⚠️ ตลาดเคลื่อนที่ในกรอบแคบ (Sideways/Weak Trend) ระวังสัญญาณหลอก (Whipsaws)")
    if bb_squeeze:
        warnings.append("⚡ เกิด Bollinger Band Squeeze! ความผันผวนบีบตัวต่ำสุด คาดว่าจะเบรกเอาต์รุนแรงเร็ว ๆ นี้")
        
    warning_text = " | ".join(warnings) if warnings else "ตลาดเคลื่อนไหวปกติเชิงโครงสร้าง"
            
    # Calculate TP and SL
    sl = 0.0
    tp1 = 0.0
    tp2 = 0.0
    rr_ratio = 1.5
    
    if "BUY" in decision:
        # Stop loss: slightly below support level, or Entry - 2 * ATR
        sl_structural = support
        sl_atr = price - (2.0 * atr) if atr > 0 else price * 0.98
        sl = max(sl_structural, sl_atr) if sl_structural > 0 else sl_atr
        if price - sl < price * 0.002: 
            sl = price - (1.5 * atr) if atr > 0 else price * 0.98
            
        risk = price - sl
        tp1 = price + (risk * rr_ratio)
        tp2 = max(resistance, price + (risk * 2.0)) if resistance > price else price + (risk * 2.0)
        
    elif "SELL" in decision:
        # Stop loss: slightly above resistance level, or Entry + 2 * ATR
        sl_structural = resistance
        sl_atr = price + (2.0 * atr) if atr > 0 else price * 1.02
        sl = min(sl_structural, sl_atr) if sl_structural > 0 else sl_atr
        if sl - price < price * 0.002:
            sl = price + (1.5 * atr) if atr > 0 else price * 1.02
            
        risk = sl - price
        tp1 = price - (risk * rr_ratio)
        tp2 = min(support, price - (risk * 2.0)) if support < price and support > 0 else price - (risk * 2.0)
        
    return {
        "Decision": decision,
        "Confidence": confidence,
        "Entry": price,
        "StopLoss": sl,
        "TakeProfit1": tp1,
        "TakeProfit2": tp2,
        "Risk": price - sl if "BUY" in decision else sl - price,
        "Warning": warning_text,
        "ADX": adx,
        "BBSqueeze": bb_squeeze
    }
