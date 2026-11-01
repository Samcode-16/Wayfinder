import httpx

from ..config import settings


async def geocode(query: str) -> dict | None:
    """Geocode a location query. Uses Geoapify if configured, otherwise OpenStreetMap Nominatim."""
    if not query:
        return None

    # 1. Geoapify Geocoding (if API key is set)
    if settings.geoapify_api_key:
        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout) as c:
                r = await c.get(
                    "https://api.geoapify.com/v1/geocode/search",
                    params={"text": query, "limit": 1, "apiKey": settings.geoapify_api_key},
                )
                if r.status_code == 200:
                    data = r.json()
                    features = data.get("features", [])
                    if features:
                        props = features[0].get("properties", {})
                        country_code = (props.get("country_code") or "").upper()
                        country = props.get("country")
                        lat = float(props["lat"])
                        lon = float(props["lon"])
                        name = props.get("formatted") or props.get("name") or query
                        return {
                            "lat": lat,
                            "lon": lon,
                            "name": name,
                            "country_code": country_code,
                            "country": country,
                        }
        except Exception:
            pass  # Fall back to Nominatim on network/API failure

    # 2. OpenStreetMap Nominatim lookup (free fallback)
    try:
        async with httpx.AsyncClient(
            timeout=settings.http_timeout, headers={"User-Agent": settings.user_agent}
        ) as c:
            r = await c.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 1},
            )
            r.raise_for_status()
            data = r.json()
        if not data:
            return None
        top = data[0]
        address = top.get("address") or {}
        country_code = (address.get("country_code") or "").upper()
        country = address.get("country")
        return {
            "lat": float(top["lat"]),
            "lon": float(top["lon"]),
            "name": top.get("display_name", query),
            "country_code": country_code,
            "country": country,
        }
    except Exception:
        return None
