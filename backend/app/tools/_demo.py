"""Deterministic demo data so the app works without any paid API key. Always labelled source='demo'."""
import hashlib
import random

from ..schemas import FlightLeg, FlightOption, HotelOption, TripRequest

AIRLINES = ["SkyJet", "Aero Nova", "BlueWing", "Horizon Air", "Globe Airways"]
HUBS = ["DXB", "FRA", "AMS", "IST", "DOH"]


def _rng(*parts: str) -> random.Random:
    return random.Random(int(hashlib.md5("|".join(parts).encode()).hexdigest()[:12], 16))


def demo_flights(req: TripRequest, fx: float) -> list[FlightOption]:
    o, d = req.origin_iata or "ORG", req.destination_iata or "DST"
    rng = _rng(o, d, req.start_date or "", req.end_date or "")
    base_usd = rng.randint(180, 780)
    out = []
    for i, stops in enumerate([0, 0, 1, 1, 1, 2]):
        airline = AIRLINES[(i + rng.randint(0, 4)) % len(AIRLINES)]
        hubs = rng.sample(HUBS, stops)
        points = [o, *hubs, d]
        dur = 120 + rng.randint(0, 420) + stops * 150
        legs = [
            FlightLeg(airline=airline, flight_number=f"{airline[:2].upper()}{rng.randint(100, 999)}",
                      from_airport=points[k], to_airport=points[k + 1],
                      departs=f"{req.start_date} {6 + 2 * k + i:02d}:{rng.choice(['00', '15', '30', '45'])}",
                      duration_min=dur // (stops + 1))
            for k in range(stops + 1)
        ]
        price = base_usd * (1 - 0.1 * stops) * (0.9 + 0.25 * rng.random()) * fx
        out.append(FlightOption(
            id=f"demo-f{i}", airline=airline, price=round(price), currency=req.currency, stops=stops,
            total_duration_min=dur, legs=legs, source="demo",
        ))
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
