import re

import httpx

from ..config import settings
from ..schemas import HotelOption, TripRequest
from ._demo import demo_hotels


async def _serpapi(req: TripRequest) -> list[HotelOption]:
    params = {
        "engine": "google_hotels", "q": f"{req.destination} hotels", "check_in_date": req.start_date,
        "check_out_date": req.end_date, "adults": req.travelers, "currency": req.currency,
        "hl": "en", "api_key": settings.serpapi_api_key,
    }
    if req.hotel_stars:
        params["hotel_class"] = ",".join(str(s) for s in range(req.hotel_stars, 6))
    async with httpx.AsyncClient(timeout=settings.http_timeout + 15) as c:
        r = await c.get("https://serpapi.com/search.json", params=params)
        r.raise_for_status()
        data = r.json()
    out: list[HotelOption] = []
    for i, p in enumerate(data.get("properties", [])):
        price = (p.get("rate_per_night") or {}).get("extracted_lowest")
        if not price:
            continue
        m = re.search(r"(\d)", str(p.get("extended_hotel_class") or p.get("hotel_class") or ""))
        gps = p.get("gps_coordinates") or {}
        imgs = p.get("images") or []
        out.append(HotelOption(
            id=p.get("property_token") or f"serp-h{i}", name=p.get("name", "Hotel"),
            price_per_night=float(price), currency=req.currency, rating=p.get("overall_rating"),
            stars=int(m.group(1)) if m else None,
            image=(imgs[0].get("thumbnail") if imgs else None), link=p.get("link"),
            lat=gps.get("latitude"), lon=gps.get("longitude"),
            amenities=(p.get("amenities") or [])[:6], source="serpapi",
        ))
    return out[:12]


async def search_hotels(req: TripRequest, fx: float = 1.0) -> tuple[list[HotelOption], list[str]]:
    warnings: list[str] = []
    if not settings.serpapi_api_key:
        warnings.append("Hotels are demo data (set SERPAPI_API_KEY for live Google Hotels prices).")
    else:
        try:
            live = await _serpapi(req)
            if live:
                return live, warnings
            warnings.append(f"No live hotels returned for '{req.destination}'; showing demo hotels.")
        except Exception as e:
            warnings.append(f"Live hotel search failed ({type(e).__name__}); showing demo hotels.")
    return demo_hotels(req, fx), warnings
