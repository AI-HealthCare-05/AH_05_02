import asyncio
import time

import httpx
import pytest

from app.services.forest_weather import ForestWeather


def test_neighbourhood_weather_cache_and_outage(monkeypatch):
    requests = []
    fail = False

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, params):
            requests.append(params)
            if fail:
                raise httpx.ConnectError("offline")
            return httpx.Response(200, request=httpx.Request("GET", url), json={
                "current": {"temperature_2m": 24.3, "weather_code": 2, "time": "2026-09-03T18:00"},
            })

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    service = ForestWeather()

    async def run():
        nonlocal fail
        first = await service.get()
        assert first["temperature"] == 24.3
        assert not first["stale"]
        assert await service.get() == first
        assert len(requests) == 1
        assert requests[0]["latitude"] == 37.51799
        assert requests[0]["timezone"] == "Asia/Seoul"
        assert "address" not in requests[0]
        fail = True
        service.updated = time.monotonic() - 700
        assert (await service.get())["stale"]
        await service.get()
        assert len(requests) == 2  # retry backoff
        service.updated = time.monotonic() - 4000
        with pytest.raises(RuntimeError):
            await service.get()
        service.value = None
        with pytest.raises(RuntimeError):
            await service.get()

    asyncio.run(run())
