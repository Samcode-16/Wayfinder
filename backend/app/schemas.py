import math
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

QUESTIONS = {
    "origin": "Where will you be travelling from?",
    "destination": "Where would you like to go?",
    "dates": "What are your travel dates? (They must be in the future, with the return after departure.)",
}


def _iso_or_none(v):
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        return None


class TripRequest(BaseModel):
    """Structured trip requirements extracted from the conversation."""

    origin: str | None = Field(None, description="City the traveler departs from")
    origin_iata: str | None = Field(None, description="IATA code of the main airport for the origin city")
    destination: str | None = Field(None, description="Destination city")
    destination_iata: str | None = Field(None, description="IATA code of the main airport for the destination")
    start_date: str | None = Field(None, description="Departure date, YYYY-MM-DD")
    end_date: str | None = Field(None, description="Return date, YYYY-MM-DD")
    travelers: int = Field(1, description="Number of travelers")
    budget: float | None = Field(None, description="Total budget for ALL travelers, only if the user stated one")
    currency: str = Field("USD", description="ISO 4217 currency code of the budget or trip")
    hotel_stars: int | None = Field(None, description="Minimum hotel star rating (1-5) if requested")
    interests: list[str] = Field(default_factory=list, description="e.g. food, museums, hiking, nightlife")
    notes: str | None = Field(None, description="Other constraints or preferences")

    def model_post_init(self, __context):
        from .tools.currency import resolve_currency_for_origin

        # If currency wasn't set or was left as default USD, infer from origin country
        if not self.currency or self.currency == "USD":
            inferred = resolve_currency_for_origin(self.origin, self.origin_iata)
            if inferred:
                self.currency = inferred
            elif not self.currency:
                self.currency = "USD"

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _dates(cls, v):
        return _iso_or_none(v)

    @field_validator("origin_iata", "destination_iata", mode="before")
    @classmethod
    def _iata(cls, v):
        v = (v or "").strip().upper()
        return v if re.fullmatch(r"[A-Z]{3}", v) else None

    @field_validator("travelers", mode="before")
    @classmethod
    def _travelers(cls, v):
        try:
            return min(max(int(v), 1), 9)
        except (TypeError, ValueError):
            return 1

    @field_validator("currency", mode="before")
    @classmethod
    def _currency(cls, v):
        v = (str(v) if v is not None else "").strip().upper()
        return v if re.fullmatch(r"[A-Z]{3}", v) else ""

    @field_validator("hotel_stars", mode="before")
    @classmethod
    def _stars(cls, v):
        try:
            return min(max(int(v), 1), 5) if v is not None else None
        except (TypeError, ValueError):
            return None

    def problems(self, today: date | None = None) -> list[str]:
        today = today or date.today()
        out: list[str] = []
        if not self.origin:
            out.append("origin")
        if not self.destination:
            out.append("destination")
        if not (self.start_date and self.end_date):
            out.append("dates")
        else:
            s, e = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
            if e <= s or s < today:
                out.append("dates")
        return out

    @property
    def start(self) -> date:
        return date.fromisoformat(self.start_date)  # type: ignore[arg-type]

    @property
    def end(self) -> date:
        return date.fromisoformat(self.end_date)  # type: ignore[arg-type]

    @property
    def nights(self) -> int:
        return (self.end - self.start).days

    @property
    def rooms(self) -> int:
        return math.ceil(self.travelers / 2)


class FlightLeg(BaseModel):
    airline: str
    flight_number: str | None = None
    from_airport: str
    to_airport: str
    departs: str | None = None
    arrives: str | None = None
    duration_min: int | None = None


class FlightOption(BaseModel):
    id: str
    airline: str
    airline_logo: str | None = None
    price: float
    currency: str
    stops: int
    total_duration_min: int
    legs: list[FlightLeg]
    link: str | None = None
    source: Literal["serpapi", "demo"]


class HotelOption(BaseModel):
    id: str
    name: str
    price_per_night: float
    currency: str
    rating: float | None = None
    stars: int | None = None
    image: str | None = None
    link: str | None = None
    lat: float | None = None
    lon: float | None = None
    amenities: list[str] = Field(default_factory=list)
    source: Literal["serpapi", "demo"]


class Activity(BaseModel):
    name: str
    category: str
    lat: float
    lon: float
    wikipedia: str | None = None


class DayWeather(BaseModel):
    date: str
    summary: str
    tmax: float | None = None
    tmin: float | None = None
    rain_prob: int | None = None
    precip_mm: float | None = None
    kind: Literal["forecast", "historical"]


class Selection(BaseModel):
    flight_id: str
    hotel_id: str
    flights_cost: float
    hotel_cost: float
    daily_cost: float
    total: float
    budget: float | None = None
    within_budget: bool = True
    currency: str
    notes: list[str] = Field(default_factory=list)


class ItineraryItem(BaseModel):
    time_of_day: Literal["morning", "afternoon", "evening"]
    title: str
    description: str = Field(..., description="Short 1-sentence description")
    place: str | None = Field(None, description="Exact name from candidate_places, or the hotel name, else null")
    est_cost: float | None = Field(None, description="Estimated cost per person in the trip currency")
    lat: float | None = Field(None, description="Leave null; filled in by the system")
    lon: float | None = Field(None, description="Leave null; filled in by the system")

    @field_validator("time_of_day", mode="before")
    @classmethod
    def _normalize_tod(cls, v):
        v = str(v).lower().strip()
        if v in ("morning", "breakfast", "dawn"):
            return "morning"
        if v in ("evening", "night", "dinner", "sunset"):
            return "evening"
        return "afternoon"


class DayPlan(BaseModel):
    date: str
    theme: str = Field("Highlights & Exploration", description="Theme for the day")
    items: list[ItineraryItem]


class TripPlan(BaseModel):
    title: str
    summary: str
    days: list[DayPlan]
    tips: list[str] = Field(default_factory=list, description="2-3 short practical travel tips")
    local_currency: str | None = Field(None, description="ISO 4217 code of the destination's currency")
    exchange_rate: float | None = Field(None, description="Leave null; filled in by the system")
