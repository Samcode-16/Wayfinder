"""Deterministic budget optimizer: picks the best flight + hotel combination that fits the budget."""
from .schemas import FlightOption, HotelOption, Selection, TripRequest

# Assumption: Google Flights prices are per traveler for the round trip.
FLIGHT_PRICE_IS_PER_TRAVELER = True
# What an hour of travel time is "worth" and the penalty per stop, in USD-ish units, for ranking flights.
VALUE_OF_TIME_PER_HOUR = 15.0
STOP_PENALTY = 40.0


def flight_score(f: FlightOption, fx: float = 1.0) -> float:
    return f.price + (VALUE_OF_TIME_PER_HOUR * fx) * f.total_duration_min / 60 + (STOP_PENALTY * fx) * f.stops


def price_selection(
    flight: FlightOption,
    hotel: HotelOption,
    req: TripRequest,
    daily_per_person: float,
    notes: list[str] | None = None,
) -> Selection:
    """Calculates pricing and budget status for a given flight and hotel pair."""
    n, nights = req.travelers, req.nights
    flight_cost = flight.price * (n if FLIGHT_PRICE_IS_PER_TRAVELER else 1)
    hotel_cost = hotel.price_per_night * nights * req.rooms
    daily_total = daily_per_person * n * (nights + 1)
    total = flight_cost + hotel_cost + daily_total

    sel_notes = list(notes) if notes is not None else []
    return Selection(
        flight_id=flight.id,
        hotel_id=hotel.id,
        flights_cost=round(flight_cost),
        hotel_cost=round(hotel_cost),
        daily_cost=round(daily_total),
        total=round(total),
        budget=req.budget,
        within_budget=(req.budget is None or total <= req.budget),
        currency=req.currency,
        notes=sel_notes,
    )


def choose(flights: list[FlightOption], hotels: list[HotelOption], req: TripRequest,
           daily_per_person: float, fx: float = 1.0) -> Selection | None:
    if not flights or not hotels:
        return None
    n, nights = req.travelers, req.nights
    flight_cost = lambda f: f.price * (n if FLIGHT_PRICE_IS_PER_TRAVELER else 1)  # noqa: E731
    hotel_cost = lambda h: h.price_per_night * nights * req.rooms  # noqa: E731
    daily_total = daily_per_person * n * (nights + 1)
    notes: list[str] = []

    flight = min(flights, key=lambda f: flight_score(f, fx))
    ranked = sorted(hotels, key=lambda h: (-(h.rating or 0), h.price_per_night))
    hotel = ranked[0]

    if req.budget:
        fits = [h for h in ranked if flight_cost(flight) + daily_total + hotel_cost(h) <= req.budget]
        if fits:
            hotel = fits[0]
            if hotel is not ranked[0]:
                notes.append("Chose the best-rated hotel that keeps the trip within budget.")
        else:
            flight, hotel = min(flights, key=lambda f: f.price), min(hotels, key=hotel_cost)
            notes.append("Nothing fits the budget; showing the cheapest flight and hotel combination.")

    return price_selection(flight, hotel, req, daily_per_person, notes=notes)
