"""MyDisease.info API client with caching support."""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx


class MyDiseaseError(Exception):
    """Custom error for MyDisease API operations."""


class CacheEntry:
    """Cache entry with expiration."""

    def __init__(self, data: Any, ttl_seconds: int = 3600):
        self.data = data
        self.expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class MyDiseaseClient:
    """Client for MyDisease.info API with optional caching."""

    def __init__(
        self,
        base_url: str = "https://mydisease.info/v1",
        timeout: float = 30.0,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
        rate_limit: Optional[int] = 10,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.rate_limit = rate_limit
        self._cache: Dict[str, CacheEntry] = {}
        self._last_request_time: Optional[datetime] = None
        self._request_count = 0

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
        return entry.data

    def _update_cache(self, cache_key: str, data: Any) -> None:
        """Update cache with new data."""
        if self.cache_enabled:
            self._cache[cache_key] = CacheEntry(data, self.cache_ttl)

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    async def _apply_rate_limit(self) -> None:
        """Apply rate limiting if configured."""
        if self.rate_limit and self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < 1.0:
                self._request_count += 1
                if self._request_count >= self.rate_limit:
                    sleep_time = 1.0 - elapsed
                    await asyncio.sleep(sleep_time)
                    self._request_count = 0
            else:
                self._request_count = 1
        else:
            self._request_count = 1

        self._last_request_time = datetime.now()

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to MyDisease API with caching."""
        cache_key = self._get_cache_key("GET", endpoint, params)
        cached_data = self._check_cache(cache_key)
        if cached_data is not None:
            return cached_data

        await self._apply_rate_limit()

        url = f"{self.base_url}/{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=self.timeout)
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

        url = f"{self.base_url}/{endpoint}"
        headers = {"content-type": "application/json"}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, json=json_data, headers=headers, timeout=self.timeout
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
        """Close any persistent resources (placeholder for future enhancements)."""
        return None
