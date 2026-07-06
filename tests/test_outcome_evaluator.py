import pytest
from tradenexus.journal.outcome import evaluate_candle_outcome

def test_buy_outcome_tp_sl():
    """
    Verifies outcome evaluation logic for BUY trades under standard TP/SL conditions.
    """
    entry = 100.0
    sl = 90.0
    tp1 = 115.0
    tp2 = 130.0
    
    # 1. SL Hit only
    status, r = evaluate_candle_outcome("BUY", entry, sl, tp1, tp2, high=105.0, low=85.0, close=95.0)
    assert status == "SL_HIT"
    assert r == -1.0
    
    # 2. TP1 Hit only
    status, r = evaluate_candle_outcome("BUY", entry, sl, tp1, tp2, high=120.0, low=95.0, close=110.0)
    assert status == "TP1_HIT"
    assert r == 1.5  # (115-100)/10 = 1.5 R
    
    # 3. TP2 Hit only
    status, r = evaluate_candle_outcome("BUY", entry, sl, tp1, tp2, high=135.0, low=95.0, close=125.0)
    assert status == "TP2_HIT"
    assert r == 3.0  # (130-100)/10 = 3.0 R

def test_sell_outcome_tp_sl():
    """
    Verifies outcome evaluation logic for SELL trades.
    """
    entry = 100.0
    sl = 110.0
    tp1 = 85.0
    tp2 = 70.0
    
    # 1. SL Hit only
    status, r = evaluate_candle_outcome("SELL", entry, sl, tp1, tp2, high=115.0, low=95.0, close=105.0)
    assert status == "SL_HIT"
    assert r == -1.0
    
    # 2. TP1 Hit only
    status, r = evaluate_candle_outcome("SELL", entry, sl, tp1, tp2, high=105.0, low=80.0, close=90.0)
    assert status == "TP1_HIT"
    assert r == 1.5
    
    # 3. TP2 Hit only
    status, r = evaluate_candle_outcome("SELL", entry, sl, tp1, tp2, high=105.0, low=65.0, close=75.0)
    assert status == "TP2_HIT"
    assert r == 3.0

def test_same_candle_conflict():
    """
    Verifies the conservative rule: if both TP and SL are hit in the same candle,
    it must return SL_HIT first.
    """
    entry = 100.0
    sl = 90.0
    tp1 = 110.0
    tp2 = 120.0
    
    # Candle has high of 115.0 (TP1 touched) and low of 85.0 (SL touched)
    status, r = evaluate_candle_outcome("BUY", entry, sl, tp1, tp2, high=115.0, low=85.0, close=100.0)
    assert status == "SL_HIT"
    assert r == -1.0
