from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from ..config import settings
from ..schemas import FlightLeg, FlightOption, TripRequest
from ._demo import demo_flights


class NearbyAirport(BaseModel):
    iata: str = Field(description="3-letter IATA airport code")
    name: str = Field(description="Airport name and city")
    distance_km: int | None = Field(None, description="Approximate distance in km from requested city")


class NearbyAirportsResult(BaseModel):
    nearby_airports: list[NearbyAirport] = Field(
        description="1-3 nearest major/international commercial airports that operate direct or major domestic/international flights"
    )


COMMON_NEARBY: dict[str, list[dict]] = {
    # India
    "MYQ": [{"iata": "BLR", "name": "Kempegowda International Airport, Bengaluru", "distance_km": 170}],
    "AGR": [{"iata": "DEL", "name": "Indira Gandhi International Airport, Delhi", "distance_km": 200}],
    "IXC": [{"iata": "DEL", "name": "Indira Gandhi International Airport, Delhi", "distance_km": 240}],
    "PNQ": [{"iata": "BOM", "name": "Chhatrapati Shivaji Maharaj International Airport, Mumbai", "distance_km": 150}],
    "BDQ": [{"iata": "AMD", "name": "Sardar Vallabhbhai Patel International Airport, Ahmedabad", "distance_km": 110}],
    "HBX": [{"iata": "BLR", "name": "Kempegowda International Airport, Bengaluru", "distance_km": 400}, {"iata": "GOI", "name": "Dabolim Airport, Goa", "distance_km": 160}],
    "PBH": [
        {"iata": "IXB", "name": "Bagdogra Airport, Siliguri (gateway to Bhutan)", "distance_km": 150},
        {"iata": "GAU", "name": "Guwahati International Airport", "distance_km": 200},
        {"iata": "DEL", "name": "Indira Gandhi International Airport, Delhi", "distance_km": 1200},
    ],
    # Europe
    "OXF": [{"iata": "LHR", "name": "London Heathrow Airport", "distance_km": 70}, {"iata": "LGW", "name": "London Gatwick Airport", "distance_km": 120}],
    "CBG": [{"iata": "STN", "name": "London Stansted Airport", "distance_km": 45}, {"iata": "LHR", "name": "London Heathrow Airport", "distance_km": 110}],
    "FLR": [{"iata": "PSA", "name": "Pisa International Airport", "distance_km": 80}, {"iata": "BLQ", "name": "Bologna Guglielmo Marconi Airport", "distance_km": 105}],
    "VRN": [{"iata": "VCE", "name": "Venice Marco Polo Airport", "distance_km": 125}, {"iata": "MXP", "name": "Milan Malpensa Airport", "distance_km": 170}],
    # US
    "SNA": [{"iata": "LAX", "name": "Los Angeles International Airport", "distance_km": 65}],
    "BUR": [{"iata": "LAX", "name": "Los Angeles International Airport", "distance_km": 45}],
    "ONT": [{"iata": "LAX", "name": "Los Angeles International Airport", "distance_km": 90}],
    "OAK": [{"iata": "SFO", "name": "San Francisco International Airport", "distance_km": 30}],
    "SJC": [{"iata": "SFO", "name": "San Francisco International Airport", "distance_km": 50}],
    "HPN": [{"iata": "JFK", "name": "John F. Kennedy International Airport, New York", "distance_km": 50}],
    "PVD": [{"iata": "BOS", "name": "Boston Logan International Airport", "distance_km": 90}],
}

_NEARBY_CACHE: dict[str, list[NearbyAirport]] = {}


async def get_nearby_airports(place: str, iata: str | None = None) -> list[NearbyAirport]:
    key = (iata or place or "").upper().strip()
    if not key:
        return []
    if key in _NEARBY_CACHE:
        return _NEARBY_CACHE[key]
    if iata and iata.upper() in COMMON_NEARBY:
        res = [NearbyAirport(**item) for item in COMMON_NEARBY[iata.upper()]]
        _NEARBY_CACHE[key] = res
        return res
    try:
        from ..llm import structured_llm

        prompt = (
            f"What are the 2-3 nearest major commercial international/domestic airports to {place} "
            f"(IATA: {iata or 'N/A'}) that operate major domestic or international flights? "
            f"Only include different airports, not the same one."
        )
        data: NearbyAirportsResult = await structured_llm(NearbyAirportsResult).ainvoke(prompt)
        res = [
            a for a in data.nearby_airports
            if a.iata and a.iata.upper() != (iata or "").upper()
        ][:3]
        _NEARBY_CACHE[key] = res
        return res
    except Exception:
        return []


def google_flights_link(origin: str, destination: str, start_date: str | None, end_date: str | None) -> str:
    q = f"Flights to {destination} from {origin} on {start_date} through {end_date}"
    return f"https://www.google.com/travel/flights?q={quote(q)}"


def curate_flight_options(options: list[FlightOption], target_total: int = 14) -> list[FlightOption]:
    """Curates flights so cheapest options (both direct and layover) are shown first,
    while direct flights (even if costlier) are preserved below them.
    The final list is strictly ordered from cheapest to costliest.
    """
    if not options:
        return []

    # Deduplicate identical flights: (airline, departure_time, price, stops)
    seen = set()
    unique_options: list[FlightOption] = []
    for f in options:
        dep_time = f.legs[0].departs if f.legs else ""
        key = (f.airline, dep_time, f.price, f.stops)
        if key not in seen:
            seen.add(key)
            unique_options.append(f)

    directs = [f for f in unique_options if f.stops == 0]
    layovers = [f for f in unique_options if f.stops > 0]

    directs.sort(key=lambda f: (f.price, f.total_duration_min))
    layovers.sort(key=lambda f: (f.price, f.total_duration_min))

    from collections import defaultdict

    def _sample_diverse(pool: list[FlightOption], limit: int, max_per_carrier: int = 2) -> list[FlightOption]:
        counts = defaultdict(int)
        picked: list[FlightOption] = []
        overflow: list[FlightOption] = []
        for f in pool:
            carrier = f.airline.split(" / ")[0].strip()
            if counts[carrier] < max_per_carrier:
                counts[carrier] += 1
                picked.append(f)
                if len(picked) >= limit:
                    break
            else:
                overflow.append(f)
        if len(picked) < limit:
            for f in overflow:
                picked.append(f)
                if len(picked) >= limit:
                    break
        return picked

    if not directs:
        selected = _sample_diverse(layovers, target_total, max_per_carrier=3)
    elif not layovers:
        selected = _sample_diverse(directs, target_total, max_per_carrier=3)
    else:
        # Both direct and layover options exist:
        # Guarantee inclusion of cheapest layovers AND direct flights (even if more costly)
        n_direct = min(len(directs), max(5, target_total // 2))
        n_layover = min(len(layovers), target_total - n_direct)

        sel_directs = _sample_diverse(directs, n_direct, max_per_carrier=2)
        sel_layovers = _sample_diverse(layovers, n_layover, max_per_carrier=2)

        combined_ids = {f.id for f in sel_directs + sel_layovers}
        remaining = [f for f in directs + layovers if f.id not in combined_ids]
        remaining.sort(key=lambda f: (f.price, f.stops, f.total_duration_min))

        needed = target_total - len(combined_ids)
        extra = remaining[:needed] if needed > 0 else []
        selected = sel_directs + sel_layovers + extra

    # Strictly sort from cheaper to costlier
    selected.sort(key=lambda f: (f.price, f.stops, f.total_duration_min))
    return selected


async def _serpapi(
    req: TripRequest,
    dep_iata: str | None = None,
    arr_iata: str | None = None,
    dep_label: str | None = None,
    arr_label: str | None = None,
) -> list[FlightOption]:
    dep = (dep_iata or req.origin_iata or "").upper()
    arr = (arr_iata or req.destination_iata or "").upper()
    dep_text = dep_label or req.origin or dep
    arr_text = arr_label or req.destination or arr

    params = {
        "engine": "google_flights",
        "departure_id": dep,
        "arrival_id": arr,
        "outbound_date": req.start_date,
        "return_date": req.end_date,
        "adults": req.travelers,
        "currency": req.currency,
        "hl": "en",
        "api_key": settings.serpapi_api_key,
    }
    async with httpx.AsyncClient(timeout=settings.http_timeout + 15) as c:
        r = await c.get("https://serpapi.com/search.json", params=params)
        r.raise_for_status()
        data = r.json()
    link = google_flights_link(dep_text, arr_text, req.start_date, req.end_date)
    raw_flights = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    out: list[FlightOption] = []
    for i, f in enumerate(raw_flights):
        legs = [
            FlightLeg(
                airline=leg.get("airline", "?"),
                flight_number=leg.get("flight_number"),
                from_airport=(leg.get("departure_airport") or {}).get("id", "?"),
                to_airport=(leg.get("arrival_airport") or {}).get("id", "?"),
                departs=(leg.get("departure_airport") or {}).get("time"),
                arrives=(leg.get("arrival_airport") or {}).get("time"),
                duration_min=leg.get("duration"),
            )
            for leg in f.get("flights", [])
        ]
        if not legs or "price" not in f:
            continue

        # Multi-carrier or feeder naming (e.g. Air India Express + Air India)
        leg_airlines = [leg.airline for leg in legs if leg.airline and leg.airline != "?"]
        unique_airlines = list(dict.fromkeys(leg_airlines))
        if not unique_airlines:
            primary_airline = "?"
        elif len(unique_airlines) == 1:
            primary_airline = unique_airlines[0]
        else:
            primary_airline = " / ".join(unique_airlines)

        out.append(
            FlightOption(
                id=f"serp-{dep}-{arr}-f{i}",
                airline=primary_airline,
                airline_logo=f.get("airline_logo"),
                price=float(f["price"]),
                currency=req.currency,
                stops=len(legs) - 1,
                total_duration_min=int(f.get("total_duration") or sum(l.duration_min or 0 for l in legs)),
                legs=legs,
                link=link,
                source="serpapi",
            )
        )
    return curate_flight_options(out, target_total=14)


async def search_flights(req: TripRequest, fx: float = 1.0) -> tuple[list[FlightOption], list[str]]:
    warnings: list[str] = []
    if not settings.serpapi_api_key:
        warnings.append("Flights are demo data (set SERPAPI_API_KEY for live Google Flights prices).")
        options = demo_flights(req, fx)
        link = google_flights_link(req.origin or "", req.destination or "", req.start_date, req.end_date)
        for o in options:
            o.link = link
        return options, warnings

    if not (req.origin_iata and req.destination_iata):
        missing = []
        if not req.origin_iata:
            missing.append(f"origin airport code for '{req.origin or 'origin'}'")
        if not req.destination_iata:
            missing.append(f"destination airport code for '{req.destination or 'destination'}'")
        warnings.append(f"Could not determine {' and '.join(missing)}; showing demo flights.")
        options = demo_flights(req, fx)
        link = google_flights_link(req.origin or "", req.destination or "", req.start_date, req.end_date)
        for o in options:
            o.link = link
        return options, warnings

    # Step 1: Query requested origin -> destination
    direct_opts: list[FlightOption] = []
    try:
        direct_opts = await _serpapi(req, req.origin_iata, req.destination_iata, req.origin, req.destination)
    except Exception as e:
        warnings.append(f"Live flight search failed ({type(e).__name__}).")

    has_nonstop = any(f.stops == 0 for f in direct_opts)
    if has_nonstop:
        return direct_opts, warnings

    # Step 2: No direct flights from the requested origin (either 0 flights, or only connecting flights).
    # Check nearest major airports to the origin!
    nearby_origins = await get_nearby_airports(req.origin or req.origin_iata, req.origin_iata)
    for cand in nearby_origins:
        try:
            nearby_opts = await _serpapi(req, cand.iata, req.destination_iata, cand.name, req.destination)
            if not nearby_opts:
                continue

            nearby_has_nonstop = any(f.stops == 0 for f in nearby_opts)
            dist_str = f", ~{cand.distance_km} km away" if cand.distance_km else ""

            if nearby_has_nonstop:
                # Found direct flights from a nearby airport
                note = (
                    f"No direct flights from {req.origin} ({req.origin_iata}). "
                    f"Showing direct flights from nearby {cand.name} ({cand.iata}{dist_str})."
                )
                warnings.append(note)
                return nearby_opts, warnings
            elif not direct_opts:
                # If requested origin had zero flights at all, use nearby airport's flights
                note = (
                    f"No flights found from {req.origin} ({req.origin_iata}). "
                    f"Showing flights from nearby {cand.name} ({cand.iata}{dist_str})."
                )
                warnings.append(note)
                return nearby_opts, warnings
        except Exception:
            continue

    # Step 3: If origin search returned connecting flights and no nearby airport had direct flights, keep them
    if direct_opts:
        warnings.append(f"No direct flights from {req.origin} ({req.origin_iata}); showing available connecting flights.")
        return direct_opts, warnings

    # Step 4: If still no flights at all (0 flights), check nearest destination airports
    nearby_dests = await get_nearby_airports(req.destination or req.destination_iata, req.destination_iata)
    for cand_d in nearby_dests:
        dist_str = f", ~{cand_d.distance_km} km away" if cand_d.distance_km else ""
        # Try requested origin -> cand_d
        try:
            dest_opts = await _serpapi(req, req.origin_iata, cand_d.iata, req.origin, cand_d.name)
            if dest_opts:
                warnings.append(
                    f"No flights found to {req.destination} ({req.destination_iata}). "
                    f"Showing flights to nearby {cand_d.name} ({cand_d.iata}{dist_str})."
                )
                return dest_opts, warnings
        except Exception:
            pass

        # Try nearest origin -> cand_d
        for cand_o in nearby_origins:
            try:
                both_opts = await _serpapi(req, cand_o.iata, cand_d.iata, cand_o.name, cand_d.name)
                if both_opts:
                    warnings.append(
                        f"No flights found between {req.origin} ({req.origin_iata}) and {req.destination} ({req.destination_iata}). "
                        f"Showing flights from nearby {cand_o.name} ({cand_o.iata}) to nearby {cand_d.name} ({cand_d.iata}{dist_str})."
                    )
                    return both_opts, warnings
            except Exception:
                pass

    # Step 5: Fallback to demo flights
    warnings.append(
        f"No live flights found on Google Flights for {req.origin_iata} → {req.destination_iata} or nearby airports; showing demo flights."
    )
    link = google_flights_link(req.origin or "", req.destination or "", req.start_date, req.end_date)
    options = demo_flights(req, fx)
    for o in options:
        o.link = link
    return options, warnings
