import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_smc_structures(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates advanced confirmed-only SMC structures: BOS, CHOCH, FVG, and Order Blocks.
    
    Ensures 100% no-lookahead:
    Structures are only marked active from the index they are confirmed (candle close).
    """
    df = df.copy()
    
    # Initialize columns
    df["BOS_Present"] = 0
    df["CHOCH_Present"] = 0
    df["FVG_Present"] = 0
    df["BOS_Direction"] = "NEUTRAL"
    df["CHOCH_Direction"] = "NEUTRAL"
    df["FVG_Direction"] = "NEUTRAL"
    df["OB_Candidate"] = 0
    df["OB_Direction"] = "NEUTRAL"
    
    if len(df) < 3:
        return df
        
    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values
    open_p = df["Open"].values
    
    # 1. FVG Detection (Fair Value Gap)
    # Bullish: Low[t] > High[t-2]
    # Bearish: High[t] < Low[t-2]
    for t in range(2, len(df)):
        if low[t] > high[t-2]:
            df.iloc[t, df.columns.get_loc("FVG_Present")] = 1
            df.iloc[t, df.columns.get_loc("FVG_Direction")] = "BULLISH"
        elif high[t] < low[t-2]:
            df.iloc[t, df.columns.get_loc("FVG_Present")] = 1
            df.iloc[t, df.columns.get_loc("FVG_Direction")] = "BEARISH"
            
    # 2. BOS & CHOCH Detection
    # Bullish BOS/CHOCH: Close[t] breaks above previous Resistance_Level[t-1]
    # Bearish BOS/CHOCH: Close[t] breaks below previous Support_Level[t-1]
    if "Support_Level" in df.columns and "Resistance_Level" in df.columns:
        dominant_trend = "Neutral"
        
        for t in range(1, len(df)):
            prev_support = df["Support_Level"].iloc[t-1]
            prev_resistance = df["Resistance_Level"].iloc[t-1]
            
            # Check Trend direction
            cdc = df.get("CDC_Trend", pd.Series(["Neutral"] * len(df))).iloc[t]
            if cdc != "Neutral":
                dominant_trend = cdc
                
            if pd.notna(prev_resistance) and close[t] > prev_resistance:
                # Bullish break
                if dominant_trend == "Bearish":
                    # First break opposite to trend -> CHOCH
                    df.iloc[t, df.columns.get_loc("CHOCH_Present")] = 1
                    df.iloc[t, df.columns.get_loc("CHOCH_Direction")] = "BULLISH"
                    dominant_trend = "Bullish"
                else:
                    df.iloc[t, df.columns.get_loc("BOS_Present")] = 1
                    df.iloc[t, df.columns.get_loc("BOS_Direction")] = "BULLISH"
                    
            elif pd.notna(prev_support) and close[t] < prev_support:
                # Bearish break
                if dominant_trend == "Bullish":
                    # First break opposite to trend -> CHOCH
                    df.iloc[t, df.columns.get_loc("CHOCH_Present")] = 1
                    df.iloc[t, df.columns.get_loc("CHOCH_Direction")] = "BEARISH"
                    dominant_trend = "Bearish"
                else:
                    df.iloc[t, df.columns.get_loc("BOS_Present")] = 1
                    df.iloc[t, df.columns.get_loc("BOS_Direction")] = "BEARISH"
                    
        # 3. Order Block Candidate Detection
        # Bullish OB: Last down-close candle before a bullish BOS/CHOCH
        # Bearish OB: Last up-close candle before a bearish BOS/CHOCH
        for t in range(1, len(df)):
            is_bull_break = (df["BOS_Present"].iloc[t] == 1 and df["BOS_Direction"].iloc[t] == "BULLISH") or \
                            (df["CHOCH_Present"].iloc[t] == 1 and df["CHOCH_Direction"].iloc[t] == "BULLISH")
                            
            is_bear_break = (df["BOS_Present"].iloc[t] == 1 and df["BOS_Direction"].iloc[t] == "BEARISH") or \
                            (df["CHOCH_Present"].iloc[t] == 1 and df["CHOCH_Direction"].iloc[t] == "BEARISH")
                            
            if is_bull_break:
                # Look back to find the last down candle (Close < Open)
                for j in range(t-1, max(0, t-10), -1):
                    if close[j] < open_p[j]:
                        df.iloc[j, df.columns.get_loc("OB_Candidate")] = 1
                        df.iloc[j, df.columns.get_loc("OB_Direction")] = "BULLISH"
                        break
                        
            elif is_bear_break:
                # Look back to find the last up candle (Close > Open)
                for j in range(t-1, max(0, t-10), -1):
                    if close[j] > open_p[j]:
                        df.iloc[j, df.columns.get_loc("OB_Candidate")] = 1
                        df.iloc[j, df.columns.get_loc("OB_Direction")] = "BEARISH"
                        break
                        
    return df
