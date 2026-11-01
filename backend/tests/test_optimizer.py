from datetime import date, timedelta

from app.optimizer import choose
from app.schemas import FlightLeg, FlightOption, HotelOption, TripRequest


def _req(budget):
    s = date.today() + timedelta(days=30)
    return TripRequest(origin="Madrid", destination="Amsterdam", start_date=s.isoformat(),
                       end_date=(s + timedelta(days=4)).isoformat(), travelers=2, budget=budget, currency="EUR")


def _flight(i, price, mins, stops):
    leg = FlightLeg(airline="X", from_airport="MAD", to_airport="AMS")
    return FlightOption(id=f"f{i}", airline="X", price=price, currency="EUR", stops=stops,
                        total_duration_min=mins, legs=[leg], source="demo")


def _hotel(i, price, rating):
    return HotelOption(id=f"h{i}", name=f"H{i}", price_per_night=price, currency="EUR", rating=rating, source="demo")


FLIGHTS = [_flight(1, 200, 150, 0), _flight(2, 150, 600, 2)]
HOTELS = [_hotel(1, 300, 4.8), _hotel(2, 120, 4.2), _hotel(3, 60, 3.5)]


def test_prefers_fast_flight_over_marginally_cheaper_slow_one():
    sel = choose(FLIGHTS, HOTELS, _req(None), 50)
    assert sel.flight_id == "f1" and sel.hotel_id == "h1"  # no budget -> best rated


def test_picks_best_rated_hotel_within_budget():
    # flights 2*200=400, daily 50*2*5=500, hotel h2 = 120*4*1 = 480 -> 1380; h1 = 1200 -> 2100
    sel = choose(FLIGHTS, HOTELS, _req(1500), 50)
    assert sel.hotel_id == "h2" and sel.within_budget and sel.total <= 1500


def test_over_budget_falls_back_to_cheapest_and_flags_it():
    sel = choose(FLIGHTS, HOTELS, _req(300), 50)
    assert sel.flight_id == "f2" and sel.hotel_id == "h3" and not sel.within_budget


def test_empty_inputs():
    assert choose([], HOTELS, _req(None), 50) is None
