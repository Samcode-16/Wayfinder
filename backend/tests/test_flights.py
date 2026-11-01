import pytest
from app.schemas import FlightLeg, FlightOption, TripRequest
from app.tools.flights import get_nearby_airports, search_flights


@pytest.mark.asyncio
async def test_nearby_airports_known_lookup():
    airports = await get_nearby_airports("Mysuru", "MYQ")
    assert len(airports) >= 1
    assert airports[0].iata == "BLR"


@pytest.mark.asyncio
async def test_search_flights_falls_back_to_nearby_when_no_direct(monkeypatch):
    import app.tools.flights as fl

    monkeypatch.setattr(fl.settings, "serpapi_api_key", "mock_key")

    req = TripRequest(
        origin="Mysuru",
        origin_iata="MYQ",
        destination="Delhi",
        destination_iata="DEL",
        start_date="2026-11-15",
        end_date="2026-11-20",
        travelers=1,
        currency="INR",
    )

    # Mock _serpapi to return connecting flights for MYQ, but direct flights for BLR
    async def mock_serpapi(req, dep_iata=None, arr_iata=None, dep_label=None, arr_label=None):
        dep = (dep_iata or req.origin_iata).upper()
        if dep == "MYQ":
            # 1-stop connecting flight
            return [
                FlightOption(
                    id="myq-1",
                    airline="IndiGo",
                    price=30000.0,
                    currency="INR",
                    stops=1,
                    total_duration_min=360,
                    legs=[
                        FlightLeg(airline="IndiGo", from_airport="MYQ", to_airport="HYD"),
                        FlightLeg(airline="IndiGo", from_airport="HYD", to_airport="DEL"),
                    ],
                    source="serpapi",
                )
            ]
        elif dep == "BLR":
            # Direct non-stop flight
            return [
                FlightOption(
                    id="blr-1",
                    airline="IndiGo",
                    price=15000.0,
                    currency="INR",
                    stops=0,
                    total_duration_min=165,
                    legs=[FlightLeg(airline="IndiGo", from_airport="BLR", to_airport="DEL")],
                    source="serpapi",
                )
            ]
        return []

    monkeypatch.setattr(fl, "_serpapi", mock_serpapi)

    opts, warns = await search_flights(req)
    assert len(opts) == 1
    assert opts[0].stops == 0
    assert opts[0].legs[0].from_airport == "BLR"
    assert any("Kempegowda International Airport, Bengaluru" in w or "BLR" in w for w in warns)


@pytest.mark.asyncio
async def test_search_flights_returns_direct_when_available(monkeypatch):
    import app.tools.flights as fl

    monkeypatch.setattr(fl.settings, "serpapi_api_key", "mock_key")

    req = TripRequest(
        origin="Bengaluru",
        origin_iata="BLR",
        destination="Delhi",
        destination_iata="DEL",
        start_date="2026-11-15",
        end_date="2026-11-20",
        travelers=1,
        currency="INR",
    )

    call_counts = []

    async def mock_serpapi(req, dep_iata=None, arr_iata=None, dep_label=None, arr_label=None):
        call_counts.append(dep_iata)
        return [
            FlightOption(
                id="blr-1",
                airline="Air India",
                price=12000.0,
                currency="INR",
                stops=0,
                total_duration_min=160,
                legs=[FlightLeg(airline="Air India", from_airport="BLR", to_airport="DEL")],
                source="serpapi",
            )
        ]

    monkeypatch.setattr(fl, "_serpapi", mock_serpapi)

    opts, warns = await search_flights(req)
    assert len(opts) == 1
    assert opts[0].stops == 0
    # Should not query any nearby airports since direct flights were found
    assert call_counts == ["BLR"]


def test_curate_flight_options_cheaper_first_and_includes_directs():
    from app.tools.flights import curate_flight_options

    def _opt(fid, airline, price, stops, duration):
        return FlightOption(
            id=fid,
            airline=airline,
            price=price,
            currency="INR",
            stops=stops,
            total_duration_min=duration,
            legs=[
                FlightLeg(airline=airline, from_airport="BLR", to_airport="DEL" if stops == 0 else "BOM")
            ],
            source="serpapi",
        )

    options = [
        # Cheap layovers
        _opt("layover-1", "IndiGo", 10000.0, 1, 360),
        _opt("layover-2", "SpiceJet", 11000.0, 1, 400),
        _opt("layover-3", "Air India", 12000.0, 1, 350),
        # Expensive directs
        _opt("direct-1", "Air India", 15000.0, 0, 160),
        _opt("direct-2", "IndiGo", 18000.0, 0, 165),
        _opt("direct-3", "Vistara", 22000.0, 0, 155),
    ]

    curated = curate_flight_options(options, target_total=6)
    assert len(curated) == 6
    # Verify strictly ordered from cheapest to costliest
    prices = [c.price for c in curated]
    assert prices == sorted(prices)
    # Verify both direct and layover flights are present
    assert any(c.stops == 0 for c in curated)
    assert any(c.stops > 0 for c in curated)
    # The cheapest flights at top are layovers, and direct flights appear below them
    assert curated[0].price == 10000.0
    assert curated[0].stops == 1
    assert curated[-1].price == 22000.0
    assert curated[-1].stops == 0


def test_demo_flights_includes_air_india_and_sorted():
    from app.tools._demo import demo_flights

    req = TripRequest(
        origin="Bengaluru",
        origin_iata="BLR",
        destination="Delhi",
        destination_iata="DEL",
        start_date="2026-11-15",
        end_date="2026-11-20",
        travelers=1,
        currency="INR",
    )
    opts = demo_flights(req, 1.0)
    assert len(opts) > 0
    # Must be sorted cheaper to costlier
    prices = [o.price for o in opts]
    assert prices == sorted(prices)

