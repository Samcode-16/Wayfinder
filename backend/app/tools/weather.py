from datetime import date, timedelta

import httpx

from ..config import settings
from ..schemas import DayWeather

WMO = {
    0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 61: "Light rain", 63: "Rain",
    65: "Heavy rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers",
    81: "Rain showers", 82: "Violent showers", 95: "Thunderstorm", 96: "Thunderstorm with hail",
    99: "Thunderstorm with hail",
}


def _shift_year(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year - years, day=28)


async def get_weather(lat: float, lon: float, start: date, end: date) -> list[DayWeather]:
    """Real forecast when the trip is within 15 days, otherwise last year's observed weather."""
    today = date.today()
    base = {"latitude": lat, "longitude": lon, "timezone": "auto"}
    async with httpx.AsyncClient(timeout=settings.http_timeout) as c:
        if end <= today + timedelta(days=15):
            kind = "forecast"
            r = await c.get(
                "https://api.open-meteo.com/v1/forecast",
                params={**base, "start_date": start.isoformat(), "end_date": end.isoformat(),
                        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"},
            )
        else:
            kind = "historical"
            shift = 1
            while _shift_year(end, shift) >= today - timedelta(days=7):
                shift += 1
            r = await c.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={**base, "start_date": _shift_year(start, shift).isoformat(),
                        "end_date": _shift_year(end, shift).isoformat(),
                        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"},
            )
        r.raise_for_status()
        d = r.json()["daily"]

    out = []
    for i in range(len(d["time"])):
        prob = (d.get("precipitation_probability_max") or [None] * (i + 1))[i]
        mm = (d.get("precipitation_sum") or [None] * (i + 1))[i]
        out.append(DayWeather(
            date=(start + timedelta(days=i)).isoformat(),
            summary=WMO.get(d["weather_code"][i], "Mixed"),
            tmax=d["temperature_2m_max"][i], tmin=d["temperature_2m_min"][i],
            rain_prob=int(prob) if prob is not None else None,
            precip_mm=mm, kind=kind,
        ))
    return out
