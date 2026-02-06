"""MyDisease.info API client with caching support."""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

import httpx


class MyDiseaseError(Exception):
    """Custom error for MyDisease API operations."""


class CacheEntry:
    """Cache entry with expiration."""

    def __init__(self, data: Any, ttl_seconds: int = 3600):
        self.data = data
        self.expires_at_monotonic = time.monotonic() + ttl_seconds

    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at_monotonic


class MyDiseaseClient:
    """Client for MyDisease.info API with optional caching."""

    def __init__(
        self,
        base_url: str = "https://mydisease.info/v1",
        timeout: float = 30.0,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
        cache_max_entries: Optional[int] = 1000,
        rate_limit: Optional[int] = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.cache_max_entries = cache_max_entries if cache_max_entries and cache_max_entries > 0 else None
        self.rate_limit = rate_limit
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._window_start: Optional[float] = None
        self._request_count = 0
        self._rate_limit_lock = asyncio.Lock()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._closed = False

    def _get_cache_key(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Any = None,
    ) -> str:
        """Generate cache key from request parameters."""
        key_parts = [method, endpoint]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        if data:
            key_parts.append(json.dumps(data, sort_keys=True))
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> Optional[Any]:
        """Check if valid cached response exists."""
        if not self.cache_enabled:
            return None

        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._cache[cache_key]
            return None
        self._cache.move_to_end(cache_key)
        return entry.data

    def _update_cache(self, cache_key: str, data: Any) -> None:
        """Update cache with new data."""
        if self.cache_enabled:
            self._cache[cache_key] = CacheEntry(data, self.cache_ttl)
            self._cache.move_to_end(cache_key)
            if self.cache_max_entries is not None:
                while len(self._cache) > self.cache_max_entries:
                    self._cache.popitem(last=False)

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting if configured."""
        if not self.rate_limit:
            return

        while True:
            sleep_for = 0.0
            async with self._rate_limit_lock:
                now = time.monotonic()
                if self._window_start is None or (now - self._window_start) >= 1.0:
                    self._window_start = now
                    self._request_count = 1
                    return

                if self._request_count < self.rate_limit:
                    self._request_count += 1
                    return

                sleep_for = 1.0 - (now - self._window_start)

            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

    async def _ensure_client_open(self) -> httpx.AsyncClient:
        if self._closed:
            raise MyDiseaseError("Client is closed. Create a new MyDiseaseClient instance.")
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._http_client

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to MyDisease API with caching."""
        cache_key = self._get_cache_key("GET", endpoint, params)
        cached_data = self._check_cache(cache_key)
        if cached_data is not None:
            return cached_data

        await self._apply_rate_limit()

        try:
            response = await (await self._ensure_client_open()).get(
                endpoint.lstrip("/"), params=params
            )
            response.raise_for_status()
            data = response.json()
            self._update_cache(cache_key, data)
            return data
        except httpx.TimeoutException:
            raise MyDiseaseError("Request timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            raise MyDiseaseError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:  # pragma: no cover - unexpected runtime failure
            raise MyDiseaseError(f"Request failed: {str(e)}")

    async def post(self, endpoint: str, json_data: Any, use_cache: bool = True) -> Any:
        """Make POST request to MyDisease API with optional caching."""
        cache_key = self._get_cache_key("POST", endpoint, data=json_data)
        if use_cache:
            cached_data = self._check_cache(cache_key)
            if cached_data is not None:
                return cached_data

        await self._apply_rate_limit()

        headers = {"content-type": "application/json"}
        try:
            response = await (await self._ensure_client_open()).post(
                endpoint.lstrip("/"),
                json=json_data,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            if use_cache:
                self._update_cache(cache_key, data)
            return data
        except httpx.TimeoutException:
            raise MyDiseaseError("Request timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            raise MyDiseaseError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except Exception as e:  # pragma: no cover - unexpected runtime failure
            raise MyDiseaseError(f"Request failed: {str(e)}")

    async def close(self) -> None:
        """Close persistent resources held by the client."""
        self._closed = True
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
