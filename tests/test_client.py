"""Tests for MyDisease client behavior."""

import pytest
import httpx

from mydisease_mcp.client import MyDiseaseClient, MyDiseaseError


@pytest.mark.asyncio
async def test_reuses_single_httpx_client_for_requests():
    """Client should reuse one AsyncClient across calls."""
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        return httpx.Response(200, json={"ok": True})

    client = MyDiseaseClient(base_url="https://example.org", cache_enabled=False, rate_limit=None)
    client._http_client = httpx.AsyncClient(
        base_url=client.base_url,
        timeout=client.timeout,
        transport=httpx.MockTransport(handler),
    )

    client_id = id(client._http_client)
    await client.get("query")
    await client.post("query", {"ids": ["A"]}, use_cache=False)

    assert id(client._http_client) == client_id
    assert requests == [("GET", "/query"), ("POST", "/query")]
    await client.close()


@pytest.mark.asyncio
async def test_close_releases_http_client_and_blocks_new_requests():
    """close() should release the underlying AsyncClient."""
    client = MyDiseaseClient(base_url="https://example.org", cache_enabled=False, rate_limit=None)
    assert client._http_client is None

    await client.close()
    assert client._http_client is None

    with pytest.raises(MyDiseaseError, match="Client is closed"):
        await client.get("query")


@pytest.mark.asyncio
async def test_rate_limiter_uses_monotonic_clock(monkeypatch):
    """Rate limiter should use monotonic time and sleep when bucket is exhausted."""
    client = MyDiseaseClient(rate_limit=1)
    monotonic_values = iter([100.0, 100.1, 101.2])
    sleep_calls = []

    def fake_monotonic() -> float:
        try:
            return next(monotonic_values)
        except StopIteration:
            return 101.2

    monkeypatch.setattr("mydisease_mcp.client.time.monotonic", fake_monotonic)

    async def fake_sleep(duration: float) -> None:
        sleep_calls.append(duration)

    monkeypatch.setattr("mydisease_mcp.client.asyncio.sleep", fake_sleep)

    await client._apply_rate_limit()
    await client._apply_rate_limit()

    assert sleep_calls
    assert sleep_calls[0] > 0
    await client.close()


@pytest.mark.asyncio
async def test_cache_respects_max_entries():
    """Cache should evict least recently used entries when full."""
    client = MyDiseaseClient(cache_enabled=True, cache_max_entries=2, rate_limit=None)

    client._update_cache("a", {"v": 1})
    client._update_cache("b", {"v": 2})
    assert list(client._cache.keys()) == ["a", "b"]

    # Access `a` so it becomes most recently used.
    assert client._check_cache("a") == {"v": 1}
    assert list(client._cache.keys()) == ["b", "a"]

    # Inserting `c` should evict `b`.
    client._update_cache("c", {"v": 3})
    assert list(client._cache.keys()) == ["a", "c"]
    assert "b" not in client._cache
    await client.close()
