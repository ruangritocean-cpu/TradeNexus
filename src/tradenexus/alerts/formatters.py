import logging

logger = logging.getLogger(__name__)

def format_signal_message(ticker: str, timeframe: str, strategy: dict) -> str:
    """
    Formats the trading signal alert message with emojis for LINE/Telegram.
    
    Args:
        ticker (str): The asset symbol.
        timeframe (str): The timeframe of the signal.
        strategy (dict): Strategy details from generate_trading_signal.
        
    Returns:
        str: Formatted message.
    """
    decision = strategy.get("Decision", "NEUTRAL")
    confidence = strategy.get("Confidence", 50)
    entry = strategy.get("Entry", 0.0)
    sl = strategy.get("StopLoss", 0.0)
    tp1 = strategy.get("TakeProfit1", 0.0)
    tp2 = strategy.get("TakeProfit2", 0.0)
    warning = strategy.get("Warning", "")
    
    # Emoji based on signal direction
    if "STRONG BUY" in decision:
        signal_emoji = "🟢🟢 [STRONG BUY]"
    elif "BUY" in decision:
        signal_emoji = "🟢 [BUY]"
    elif "STRONG SELL" in decision:
        signal_emoji = "🔴🔴 [STRONG SELL]"
    elif "SELL" in decision:
        signal_emoji = "🔴 [SELL]"
    else:
        signal_emoji = "⚪ [NEUTRAL]"
        
    # Clean HTML characters for Telegram parse_mode="HTML" compatibility
    clean_warning = warning.replace("<", "&lt;").replace(">", "&gt;")
        
    msg = f"""
<b>🔔 [TradeNexus Pro Signal Alert]</b>
━━━━━━━━━━━━━━━━━━
📈 <b>Asset:</b> {ticker}
⏱️ <b>Timeframe:</b> {timeframe}
🚦 <b>Signal:</b> {signal_emoji}
🎯 <b>Confidence:</b> {confidence}%
━━━━━━━━━━━━━━━━━━
🛒 <b>Entry Price:</b> ${entry:,.2f}
🛡️ <b>Stop Loss (SL):</b> ${sl:,.2f}
🟢 <b>Take Profit 1 (TP1):</b> ${tp1:,.2f}
🟢 <b>Take Profit 2 (TP2):</b> ${tp2:,.2f}
━━━━━━━━━━━━━━━━━━
ℹ️ <b>Market State:</b>
<i>{clean_warning}</i>
"""
    return msg.strip()
