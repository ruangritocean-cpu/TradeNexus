import time
import pandas as pd
from tradenexus.data.cache import TTLCache

def test_ttl_cache_operations():
    """
    Verifies that TTLCache handles gets, sets, TTL expiration, and diagnostics counts correctly.
    """
    cache = TTLCache()
    
    # 1. Set key
    df_mock = pd.DataFrame({"Close": [10.0, 20.0]})
    cache.set("test_key", df_mock, ttl_seconds=2.0)
    
    # 2. Get key (HIT)
    val = cache.get("test_key")
    assert val is not None
    assert len(val) == 2
    
    diag = cache.get_diagnostics()
    assert diag["hits"] == 1
    assert diag["misses"] == 0
    assert diag["active_items"] == 1
    
    # 3. Expiration test
    time.sleep(2.1)
    val_expired = cache.get("test_key")
    assert val_expired is None
    
    diag_expired = cache.get_diagnostics()
    assert diag_expired["misses"] == 1  # Incremented miss
    assert diag_expired["active_items"] == 0
    
    # 4. Clear test
    cache.set("another", 42, ttl_seconds=10.0)
    cache.clear()
    diag_cleared = cache.get_diagnostics()
    assert diag_cleared["active_items"] == 0
    assert diag_cleared["hits"] == 0
