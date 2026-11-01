import pytest
from app.tools.email import generate_itinerary_html, generate_itinerary_text, is_valid_email, send_itinerary_email


MOCK_TRIP = {
    "plan": {
        "title": "5 Days in Tokyo",
        "summary": "Exploring modern highlights and historic shrines.",
        "days": [
            {
                "date": "2026-11-10",
                "theme": "Shinjuku & Shibuya",
                "items": [
                    {
                        "time_of_day": "morning",
                        "title": "Meiji Jingu Shrine",
                        "description": "Walk through serene forested pathways.",
                        "place": "Meiji Jingu",
                        "est_cost": 0,
                    },
                    {
                        "time_of_day": "afternoon",
                        "title": "Shibuya Crossing",
                        "description": "Experience the world's busiest intersection.",
                        "place": "Shibuya Crossing",
                        "est_cost": 25,
                    },
                ],
            }
        ],
        "tips": ["Get a Suica or Pasmo transit card.", "Carry some cash for local stalls."],
    },
    "request": {
        "destination": "Tokyo",
        "start_date": "2026-11-10",
        "end_date": "2026-11-15",
        "travelers": 2,
        "currency": "USD",
    },
    "selection": {
        "flight_id": "f1",
        "hotel_id": "h1",
        "flights_cost": 1200,
        "hotel_cost": 800,
        "daily_cost": 600,
        "total": 2600,
        "currency": "USD",
        "within_budget": True,
    },
    "flights": [
        {"id": "f1", "airline": "ANA", "price": 600, "stops": 0, "currency": "USD"}
    ],
    "hotels": [
        {"id": "h1", "name": "Hotel Gracery Shinjuku", "price_per_night": 160, "currency": "USD", "rating": 4.5}
    ],
}


def test_email_validation():
    assert is_valid_email("traveler@example.com")
    assert is_valid_email("name.surname+tag@sub.domain.co.uk")
    assert not is_valid_email("")
    assert not is_valid_email("invalid-email")
    assert not is_valid_email("@no-user.com")
    assert not is_valid_email("no-domain@")


def test_generate_email_text():
    text = generate_itinerary_text(MOCK_TRIP)
    assert "5 Days in Tokyo" in text
    assert "Meiji Jingu" in text
    assert "ANA" in text
    assert "Hotel Gracery Shinjuku" in text
    assert "ESTIMATED TOTAL: 2,600 USD" in text


def test_generate_email_html():
    html = generate_itinerary_html(MOCK_TRIP)
    assert "5 Days in Tokyo" in html
    assert "Meiji Jingu" in html
    assert "ANA" in html
    assert "Hotel Gracery Shinjuku" in html
    assert "2,600 USD" in html
    assert "Practical Travel Tips" in html


@pytest.mark.asyncio
async def test_send_itinerary_email_demo_mode(monkeypatch):
    from app.config import Settings
    monkeypatch.setattr("app.tools.email.Settings", lambda: Settings(smtp_host=None, resend_api_key=None, brevo_api_key=None))
    res = await send_itinerary_email("user@example.com", MOCK_TRIP)
    assert res["ok"] is True
    assert res["status"] == "demo"
    assert "user@example.com" in res["message"]


@pytest.mark.asyncio
async def test_send_itinerary_email_invalid_address():
    res = await send_itinerary_email("bad-email", MOCK_TRIP)
    assert res["ok"] is False
    assert res["status"] == "error"


@pytest.mark.asyncio
async def test_send_itinerary_email_resend_api(monkeypatch):
    from app.config import Settings
    import httpx

    monkeypatch.setattr("app.tools.email.Settings", lambda: Settings(resend_api_key="re_test_123"))

    class MockResponse:
        is_success = True
        status_code = 200

        def json(self):
            return {"id": "msg_123"}

    async def mock_post(self, url, headers=None, json=None):
        assert "api.resend.com" in url
        assert "re_test_123" in headers.get("Authorization", "")
        assert json.get("to") == ["traveler@example.com"]
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await send_itinerary_email("traveler@example.com", MOCK_TRIP)
    assert res["ok"] is True
    assert res["status"] == "sent"
    assert "Resend" in res["message"]

