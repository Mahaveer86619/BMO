import logging
import httpx
from app.core.config import settings

log = logging.getLogger("bmo.weather")


async def get_weather(location: str | None = None) -> str:
    loc = (location or settings.DEFAULT_WEATHER_LOCATION).strip()
    url = f"https://wttr.in/{loc}?format=j1"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers={"User-Agent": "BMO/1.0"})
            r.raise_for_status()
            data = r.json()

        current = data["current_condition"][0]
        desc = current["weatherDesc"][0]["value"]
        temp_c = current["temp_C"]
        feels_c = current["FeelsLikeC"]
        humidity = current["humidity"]
        area = data["nearest_area"][0]["areaName"][0]["value"]
        country = data["nearest_area"][0]["country"][0]["value"]

        return (
            f"In {area}, {country}: {desc.lower()}, {temp_c}°C "
            f"(feels like {feels_c}°C), humidity {humidity}%."
        )
    except httpx.HTTPStatusError as e:
        log.warning("Weather HTTP error for %r: %s", loc, e)
        return f"Couldn't fetch weather for {loc!r} — location not found."
    except Exception as e:
        log.warning("Weather fetch failed: %s", e)
        return f"Couldn't fetch weather right now. Try again in a moment."
