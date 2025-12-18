"""Simple in-memory cache for API responses."""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

# Simple in-memory cache storage
_cache: Dict[str, Dict[str, Any]] = {}


def get_cache(key: str) -> Optional[Any]:
    """Get a value from cache if it exists and hasn't expired."""
    if key in _cache:
        entry = _cache[key]
        if time.time() < entry["expires_at"]:
            return entry["value"]
        else:
            # Expired, remove it
            del _cache[key]
    return None


def set_cache(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Set a value in cache with TTL (default 5 minutes)."""
    _cache[key] = {
        "value": value,
        "expires_at": time.time() + ttl_seconds,
    }


def clear_cache(pattern: Optional[str] = None) -> None:
    """Clear cache entries. If pattern provided, only clear matching keys."""
    global _cache
    if pattern is None:
        _cache = {}
    else:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _cache[key]


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live in seconds (default 5 minutes)
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}{func.__name__}"
            
            # Check cache
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            set_cache(cache_key, result, ttl_seconds)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}{func.__name__}"
            
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            set_cache(cache_key, result, ttl_seconds)
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

