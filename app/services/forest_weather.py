"""Public neighbourhood weather; never sends a visitor's address or location."""

import asyncio
import math
import time
from datetime import datetime

import httpx


class ForestWeather:
    def __init__(self) -> None:
        self.value: dict | None = None
        self.updated = 0.0
        self.retry_after = 0.0
        self.lock = asyncio.Lock()

    async def get(self) -> dict:
        async with self.lock:
            now = time.monotonic()
            if self.value and now - self.updated < 600:
                return {**self.value, "stale": False}
            if now >= self.retry_after:
                try:
                    async with httpx.AsyncClient(timeout=8) as client:
                        response = await client.get(
                            "https://api.open-meteo.com/v1/forecast",
                            params={
                                "latitude": 37.51799,
                                "longitude": 127.01285,
                                "current": "temperature_2m,weather_code",
                                "timezone": "Asia/Seoul",
                                "forecast_days": 1,
                            },
                        )
                        response.raise_for_status()
                        current = response.json()["current"]
                        temperature = float(current["temperature_2m"])
                        code = int(current["weather_code"])
                        observed = datetime.fromisoformat(current["time"]).isoformat(timespec="minutes")
                        if not math.isfinite(temperature) or not -90 <= temperature <= 65:
                            raise ValueError("invalid temperature")
                    self.value = {
                        "temperature": temperature,
                        "code": code,
                        "observedAt": observed,
                        "area": "서초구 잠원동 인근",
                        "source": "Open-Meteo",
                    }
                    self.updated = time.monotonic()
                    return {**self.value, "stale": False}
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    self.retry_after = time.monotonic() + 60
            if self.value and now - self.updated < 3600:
                return {**self.value, "stale": True}
            raise RuntimeError("weather temporarily unavailable")


forest_weather = ForestWeather()
