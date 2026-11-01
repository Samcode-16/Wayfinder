"""Deterministic demo data so the app works without any paid API key. Always labelled source='demo'."""
import hashlib
import random

from ..schemas import FlightLeg, FlightOption, HotelOption, TripRequest

AIRLINES = [
    "Air India",
    "IndiGo",
    "Air India Express",
    "Akasa Air",
    "Emirates",
    "Qatar Airways",
    "British Airways",
]
HUBS = ["DXB", "FRA", "AMS", "IST", "DOH", "DEL", "BOM"]


def _rng(*parts: str) -> random.Random:
    return random.Random(int(hashlib.md5("|".join(parts).encode()).hexdigest()[:12], 16))


def demo_flights(req: TripRequest, fx: float) -> list[FlightOption]:
    o, d = req.origin_iata or "ORG", req.destination_iata or "DST"
    rng = _rng(o, d, req.start_date or "", req.end_date or "")
    base_usd = rng.randint(180, 780)
    out = []
    # Both direct nonstops (stops=0) and layover flights (stops=1, 2)
    for i, stops in enumerate([1, 1, 2, 0, 0, 0, 1]):
        airline = AIRLINES[(i + rng.randint(0, len(AIRLINES) - 1)) % len(AIRLINES)]
        hubs = rng.sample(HUBS, stops)
        points = [o, *hubs, d]
        dur = 120 + rng.randint(0, 300) + stops * 180
        legs = [
            FlightLeg(airline=airline, flight_number=f"{airline[:2].upper()}{rng.randint(100, 999)}",
                      from_airport=points[k], to_airport=points[k + 1],
                      departs=f"{req.start_date} {6 + 2 * k + i:02d}:{rng.choice(['00', '15', '30', '45'])}",
                      duration_min=dur // (stops + 1))
            for k in range(stops + 1)
        ]
        # Direct flights can be costlier than layover flights
        stop_discount = 0.15 * stops
        # Price is total for all travelers, matching SerpApi Google Flights behavior
        price = base_usd * req.travelers * (1 - stop_discount) * (0.9 + 0.25 * rng.random()) * fx
        out.append(FlightOption(
            id=f"demo-f{i}", airline=airline, price=round(price), currency=req.currency, stops=stops,
            total_duration_min=dur, legs=legs, source="demo",
        ))
    # Optimize to show cheaper flights to costly ones
    out.sort(key=lambda f: (f.price, f.stops, f.total_duration_min))
    return out


def demo_hotels(req: TripRequest, fx: float) -> list[HotelOption]:
    dest = req.destination or "City"
    rng = _rng(dest, req.start_date or "")
    names = [("Grand", 5), ("Central Palace", 5), ("Riverside", 4), ("Boutique Loft", 4),
             ("City Comfort", 3), ("Urban Stay", 3), ("Budget Inn", 2)]
    out = []
    for i, (label, stars) in enumerate(names):
        price = (35 + stars * 38 + rng.randint(-12, 25)) * fx
        out.append(HotelOption(
            id=f"demo-h{i}", name=f"{dest} {label} Hotel", price_per_night=round(price), currency=req.currency,
            rating=round(min(4.9, 3.4 + stars * 0.25 + rng.random() * 0.4), 1), stars=stars,
            amenities=rng.sample(["Free Wi-Fi", "Breakfast", "Gym", "Pool", "Spa", "Airport shuttle", "Bar"], 4),
            source="demo",
        ))
    if req.hotel_stars:
        out = [h for h in out if (h.stars or 0) >= req.hotel_stars] or out
    return out
