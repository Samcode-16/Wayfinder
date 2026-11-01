from datetime import date, timedelta

from app.optimizer import choose, price_selection
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
    # flights 200 total, daily 50*2*5=500, hotel h2 = 120*4*1 = 480 -> 1180; h1 = 1200 -> 1900
    sel = choose(FLIGHTS, HOTELS, _req(1500), 50)
    assert sel.hotel_id == "h2" and sel.within_budget and sel.total <= 1500


def test_over_budget_falls_back_to_cheapest_and_flags_it():
    sel = choose(FLIGHTS, HOTELS, _req(300), 50)
    assert sel.flight_id == "f2" and sel.hotel_id == "h3" and not sel.within_budget


def test_empty_inputs():
    assert choose([], HOTELS, _req(None), 50) is None


def test_price_selection_reprices_on_flight_or_hotel_change():
    req = _req(1500)
    # Original choice from optimizer: f1 (total price 200), h2 (120 * 4 nights * 1 room = 480), daily 500 => total 1180
    sel = choose(FLIGHTS, HOTELS, req, 50)
    assert sel.flight_id == "f1" and sel.hotel_id == "h2" and sel.total == 1180 and sel.within_budget

    # Re-price with hotel h1 (300 * 4 = 1200), total = 200 + 1200 + 500 = 1900 (exceeds 1500 budget)
    sel_h1 = price_selection(FLIGHTS[0], HOTELS[0], req, 50, notes=["Selected luxury stay"])
    assert sel_h1.hotel_id == "h1"
    assert sel_h1.hotel_cost == 1200
    assert sel_h1.total == 1900
    assert not sel_h1.within_budget
    assert "Selected luxury stay" in sel_h1.notes

    # Re-price with flight f2 (total price 150) and hotel h3 (60 * 4 = 240), daily 500 => total 890
    sel_f2_h3 = price_selection(FLIGHTS[1], HOTELS[2], req, 50)
    assert sel_f2_h3.flight_id == "f2"
    assert sel_f2_h3.hotel_id == "h3"
    assert sel_f2_h3.flights_cost == 150
    assert sel_f2_h3.hotel_cost == 240
    assert sel_f2_h3.total == 890
    assert sel_f2_h3.within_budget
