from datetime import date, timedelta

from app.schemas import TripRequest


def test_bad_llm_output_is_sanitised():
    r = TripRequest(origin="A", destination="B", start_date="next friday", end_date="2099-02-30",
                    destination_iata="amsterdam", travelers=None, currency="euro")
    assert r.start_date is None and r.end_date is None
    assert r.destination_iata is None and r.travelers == 1 and r.currency == "USD"
    assert r.problems() == ["dates"]


def test_past_or_inverted_dates_are_flagged():
    t = date.today()
    past = TripRequest(origin="A", destination="B", start_date=(t - timedelta(days=3)).isoformat(),
                       end_date=(t + timedelta(days=3)).isoformat())
    inverted = TripRequest(origin="A", destination="B", start_date=(t + timedelta(days=9)).isoformat(),
                           end_date=(t + timedelta(days=5)).isoformat())
    assert past.problems() == ["dates"] and inverted.problems() == ["dates"]


def test_currency_inferred_from_origin_country():
    blr = TripRequest(origin="Bangalore", destination="Amsterdam")
    assert blr.currency == "INR"

    delhi = TripRequest(origin="Delhi", destination="Paris")
    assert delhi.currency == "INR"

    london = TripRequest(origin="London", destination="Amsterdam")
    assert london.currency == "GBP"

    paris = TripRequest(origin="Paris", destination="New York")
    assert paris.currency == "EUR"

    tokyo = TripRequest(origin="Tokyo", destination="Bangalore")
    assert tokyo.currency == "JPY"


def test_explicit_currency_is_respected():
    r = TripRequest(origin="Bangalore", destination="Amsterdam", currency="EUR")
    assert r.currency == "EUR"

