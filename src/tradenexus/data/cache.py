import time
import threading
import logging
from typing import Any, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class TTLCache:
    """
    A thread-safe In-Memory cache with Time-To-Live (TTL) expiration support.
    Tracks hits, misses, and provides self-healing diagnostics.
    """
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    self.hits += 1
                    logger.debug(f"Cache HIT for key: {key}")
                    return value
                else:
                    # Expired, clean up
                    del self._cache[key]
                    logger.debug(f"Cache EXPIRED for key: {key}")
            self.misses += 1
            logger.debug(f"Cache MISS for key: {key}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: float):
        with self._lock:
            expiry = time.time() + ttl_seconds
            self._cache[key] = (value, expiry)
            logger.debug(f"Cache SET for key: {key} with TTL: {ttl_seconds}s")

    def delete(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0
            logger.info("Cache cleared successfully.")

    def get_diagnostics(self) -> Dict[str, Any]:
        with self._lock:
            # Clean expired items first to give accurate count
            now = time.time()
            expired_keys = [k for k, (_, expiry) in self._cache.items() if now >= expiry]
            for k in expired_keys:
                del self._cache[k]
                
            total = self.hits + self.misses
            hit_ratio = (self.hits / total * 100.0) if total > 0 else 0.0
            return {
                "active_items": len(self._cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio_pct": hit_ratio
            }

# Global singleton cache instance
global_cache = TTLCache()

def get_interval_ttl(interval: str) -> float:
    """
    Returns appropriate cache TTL in seconds based on interval.
    - 15m: 3 minutes (180s)
    - 1h: 10 minutes (600s)
    - 4h: 30 minutes (1800s)
    - 1d: 12 hours (43200s)
    """
    interval_lower = interval.lower().strip()
    if interval_lower == "15m":
        return 180.0
    elif interval_lower == "1h":
        return 600.0
    elif interval_lower == "4h":
        return 1800.0
    elif interval_lower == "1d":
        return 43200.0
    else:
        return 300.0  # default 5 minutes
