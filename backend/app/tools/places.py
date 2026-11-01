import httpx

from ..config import settings
from ..schemas import Activity

OVERPASS = "https://overpass-api.de/api/interpreter"


def _query(lat: float, lon: float, radius: int) -> str:
    t = "attraction|museum|gallery|viewpoint|zoo|theme_park"
    h = "monument|castle|memorial|archaeological_site|ruins"
    return f"""[out:json][timeout:20];
(
  node(around:{radius},{lat},{lon})["tourism"~"^({t})$"]["name"];
  way(around:{radius},{lat},{lon})["tourism"~"^({t})$"]["name"];
  node(around:{radius},{lat},{lon})["historic"~"^({h})$"]["name"];
);
out center 120;"""


async def find_attractions(lat: float, lon: float, radius: int = 7000, limit: int = 25) -> list[Activity]:
    """Points of interest from OpenStreetMap, ranked by 'notability' (wikipedia/wikidata tags)."""
    async with httpx.AsyncClient(timeout=settings.http_timeout + 15, headers={"User-Agent": settings.user_agent}) as c:
        r = await c.post(OVERPASS, data={"data": _query(lat, lon, radius)})
        r.raise_for_status()
        elements = r.json().get("elements", [])

    scored: dict[str, tuple[int, Activity]] = {}
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        la = el.get("lat") or el.get("center", {}).get("lat")
        lo = el.get("lon") or el.get("center", {}).get("lon")
        if not (name and la and lo):
            continue
        score = (3 if "wikipedia" in tags else 0) + (2 if "wikidata" in tags else 0) + (1 if "website" in tags else 0)
        score += 1 if tags.get("tourism") in ("attraction", "museum") else 0
        act = Activity(
            name=name, category=tags.get("tourism") or tags.get("historic", "attraction"),
            lat=float(la), lon=float(lo), wikipedia=tags.get("wikipedia"),
        )
        if name not in scored or score > scored[name][0]:
            scored[name] = (score, act)
    ranked = sorted(scored.values(), key=lambda x: -x[0])
    return [a for _, a in ranked[:limit]]
