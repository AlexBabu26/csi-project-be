"""In-memory cache for API responses with TTL and pattern-based invalidation.

On Vercel (serverless / NullPool mode) each request may land in a different
worker, so this cache only helps within a single worker's lifetime. For
multi-worker deployments, replace get_cache / set_cache / clear_cache with a
Redis or Upstash client while keeping the same interface.
"""

import time
import threading
from functools import wraps
from typing import Any, Callable, Dict, Optional


_cache: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()

# Long-lived TTLs for reference / mostly-static data
TTL_DASHBOARD = 300        # 5 min
TTL_UNITS_LIST = 300       # 5 min
TTL_PAYMENTS = 120         # 2 min
TTL_MEMBER_ADD_REQ = 120   # 2 min
TTL_SITE_SETTINGS = 600    # 10 min
TTL_MASTER_DATA = 3600     # 1 hour (countries / states / cities rarely change)
TTL_KALAMELA = 300         # 5 min
TTL_DISTRICT_DATA = 300    # 5 min


def get_cache(key: str) -> Optional[Any]:
    """Return cached value if still fresh, else None."""
    with _lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        if time.monotonic() < entry["expires_at"]:
            return entry["value"]
        del _cache[key]
        return None


def set_cache(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Store *value* under *key* for *ttl_seconds* seconds."""
    with _lock:
        _cache[key] = {
            "value": value,
            "expires_at": time.monotonic() + ttl_seconds,
        }


def clear_cache(pattern: Optional[str] = None) -> None:
    """Delete cache entries whose key contains *pattern* (or all if None)."""
    with _lock:
        if pattern is None:
            _cache.clear()
        else:
            to_delete = [k for k in _cache if pattern in k]
            for key in to_delete:
                del _cache[key]


def cache_size() -> int:
    """Return number of live (non-expired) entries."""
    now = time.monotonic()
    with _lock:
        return sum(1 for e in _cache.values() if now < e["expires_at"])


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorator: cache async or sync function result by function name.

    The cache key is ``{key_prefix}{func.__name__}``.  For functions that
    accept arguments which should vary the key, use get_cache / set_cache
    directly.
    """
    def decorator(func: Callable) -> Callable:
        import asyncio

        cache_key = f"{key_prefix}{func.__name__}"

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            set_cache(cache_key, result, ttl_seconds)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            set_cache(cache_key, result, ttl_seconds)
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
