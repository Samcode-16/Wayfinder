"""LangGraph workflow.

START -> parse -> (clarify <-> parse)* -> prepare -> [flights | hotels | activities | weather] (parallel)
      -> optimize -> compose -> approve -> (compose again with feedback | END)
"""
import asyncio
import difflib
import operator
from datetime import timedelta
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from .config import settings
from .llm import structured_llm
from .optimizer import choose
from .schemas import (QUESTIONS, FlightOption, HotelOption, TripPlan, TripRequest)
from .tools.currency import get_rate
from .tools.flights import search_flights
from .tools.geo import geocode
from .tools.hotels import search_hotels
from .tools.places import find_attractions
from .tools.weather import get_weather

PARALLEL = ["flights", "hotels", "activities", "weather"]


class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    request: dict
    geo: dict | None
    fx: float
    flights: list[dict]
    hotels: list[dict]
    activities: list[dict]
    weather: list[dict]
    selection: dict | None
    plan: dict | None
    feedback: str | None
    warnings: Annotated[list[str], operator.add]  # parallel nodes append, so this needs a reducer


def emit(node: str, status: str, detail: str | None = None) -> None:
    """Push a live 'agent activity' event to the SSE stream (no-op outside a graph run)."""
    try:
        get_stream_writer()({"node": node, "status": status, "detail": detail})
    except Exception:
        pass


def _req(state: TravelState) -> TripRequest:
    return TripRequest.model_validate(state["request"])


# ---------------------------------------------------------------- understand
PARSE_PROMPT = """You extract structured trip requirements from the conversation.
Today is {today}. Resolve relative or partial dates ("Oct 1st to 7th", "next weekend") to the next future occurrence.
Give the IATA code of the main airport for origin and destination cities.
For `currency`: If the user mentions a specific currency or symbol (e.g. USD, EUR, INR, GBP, $, €, ₹, £), set the ISO 4217 code. If no currency is stated, set the ISO 4217 currency of the traveler's origin country (e.g. INR for India/Bangalore/Delhi, GBP for UK/London, EUR for Eurozone, JPY for Japan, CAD for Canada, AUD for Australia, USD for USA). NEVER set USD for an origin outside the US unless the user explicitly requested USD.
NEVER guess the origin, destination or dates: leave them null if the user has not stated them.
Merge information across all messages; later messages override earlier ones."""


async def parse_request(state: TravelState):
    import re
    from datetime import date
    from .tools.currency import resolve_currency_for_origin

    emit("parse", "start")
    sys = SystemMessage(content=PARSE_PROMPT.format(today=date.today().isoformat()))
    req: TripRequest = await structured_llm(TripRequest).ainvoke([sys, *state["messages"]])

    # If the user did not explicitly mention USD/dollar and origin is non-US, ensure origin country currency is used
    msg_text = " ".join(m.content for m in state.get("messages", []) if isinstance(m, HumanMessage)).lower()
    has_explicit_usd = bool(re.search(r"\b(usd|dollar|\$)\b", msg_text))
    if not has_explicit_usd and req.origin:
        inferred = resolve_currency_for_origin(req.origin, req.origin_iata)
        if inferred:
            req.currency = inferred

    emit("parse", "done", ", ".join(req.problems()) and f"missing: {', '.join(req.problems())}" or "request understood")
    return {"request": req.model_dump()}


def route_after_parse(state: TravelState) -> str:
    return "clarify" if _req(state).problems() else "prepare"


def clarify(state: TravelState):
    """Human-in-the-loop: pause the graph and ask the user for what's missing."""
    problems = _req(state).problems()
    answer = interrupt({
        "type": "clarify", "missing": problems,
        "questions": [QUESTIONS[p] for p in problems], "request": state["request"],
    })
    return {"messages": [HumanMessage(content=str(answer))]}


# ------------------------------------------------------------------ gather
async def _try(coro, label: str, warnings: list[str]):
    try:
        return await coro
    except Exception as e:
        warnings.append(f"{label} unavailable ({type(e).__name__}).")
        return None


async def prepare(state: TravelState):
    import re
    from .tools.currency import resolve_currency_for_origin

    emit("prepare", "start")
    req, warnings = _req(state), []
    dest_geo, origin_geo = await asyncio.gather(
        _try(geocode(req.destination), "Destination lookup", warnings),
        _try(geocode(req.origin), "Origin lookup", warnings) if req.origin else asyncio.sleep(0),
    )
    if isinstance(origin_geo, dict) and origin_geo.get("country_code"):
        msg_text = " ".join(m.content for m in state.get("messages", []) if isinstance(m, HumanMessage)).lower()
        has_explicit = bool(re.search(r"\b(usd|dollar|\$|eur|euro|€|gbp|pound|£|inr|rupee|rs|₹|jpy|yen|¥)\b", msg_text))
        if not has_explicit:
            country_curr = resolve_currency_for_origin(country_code=origin_geo.get("country_code"))
            if country_curr and country_curr != req.currency:
                req.currency = country_curr

    rate = await _try(get_rate("USD", req.currency), "Currency conversion", warnings)
    emit("prepare", "done", dest_geo["name"] if dest_geo else "destination not located")
    return {"geo": dest_geo, "fx": rate or 1.0, "warnings": warnings, "request": req.model_dump()}


async def flights_node(state: TravelState):
    emit("flights", "start")
    options, warns = await search_flights(_req(state), state.get("fx", 1.0))
    emit("flights", "done", f"{len(options)} options")
    return {"flights": [o.model_dump() for o in options], "warnings": warns}


async def hotels_node(state: TravelState):
    emit("hotels", "start")
    options, warns = await search_hotels(_req(state), state.get("fx", 1.0))
    emit("hotels", "done", f"{len(options)} options")
    return {"hotels": [o.model_dump() for o in options], "warnings": warns}


async def activities_node(state: TravelState):
    emit("activities", "start")
    geo, warns = state.get("geo"), []
    acts = await _try(find_attractions(geo["lat"], geo["lon"]), "Attraction search", warns) if geo else None
    emit("activities", "done", f"{len(acts or [])} places")
    return {"activities": [a.model_dump() for a in acts or []], "warnings": warns}


async def weather_node(state: TravelState):
    emit("weather", "start")
    geo, req, warns = state.get("geo"), _req(state), []
    days = await _try(get_weather(geo["lat"], geo["lon"], req.start, req.end), "Weather", warns) if geo else None
    emit("weather", "done", f"{len(days or [])} days")
    return {"weather": [d.model_dump() for d in days or []], "warnings": warns}


# ---------------------------------------------------------------- decide
async def optimize_node(state: TravelState):
    emit("optimize", "start")
    req = _req(state)
    flights = [FlightOption(**f) for f in state.get("flights", [])]
    hotels = [HotelOption(**h) for h in state.get("hotels", [])]
    fx = state.get("fx", 1.0)
    sel = choose(flights, hotels, req, settings.daily_spend_usd_per_person * fx, fx=fx)
    if sel is None:
        emit("optimize", "done", "nothing to price")
        return {"selection": None, "warnings": ["Could not price the trip: no flights or hotels found."]}
    emit("optimize", "done", f"total {sel.total:,.0f} {sel.currency}" + ("" if sel.within_budget else " (over budget)"))
    warns = [] if sel.within_budget else [f"Estimated total exceeds your budget of {sel.budget:,.0f} {sel.currency}."]
    return {"selection": sel.model_dump(), "warnings": warns}


COMPOSE_PROMPT = """You are an expert travel planner. Build a day-by-day itinerary from the JSON context.
Rules:
- Produce exactly one entry in `days` for each date in `days_context`, in order. Day 1 includes arrival; the last day includes departure.
- Each day has 2-4 items (morning/afternoon/evening). Group places that are close together on the same day.
- For `place`, use an EXACT name from `candidate_places` or the hotel name; otherwise null. Never invent attractions that aren't in the list unless the list is empty.
- Adapt to the weather (indoor options on rainy days) and to the traveler's interests and notes.
- Keep est_cost per person, in the trip currency (specified in trip.currency). Leave lat/lon null.
- Set local_currency to the destination's ISO 4217 currency code.
- If `feedback` is present, revise `previous_plan` to address it while keeping what the user didn't object to."""


async def compose_node(state: TravelState):
    emit("compose", "start")
    req = _req(state)
    flights = {f["id"]: f for f in state.get("flights", [])}
    hotels = {h["id"]: h for h in state.get("hotels", [])}
    sel = state.get("selection") or {}
    hotel = hotels.get(sel.get("hotel_id"))
    weather = {w["date"]: w for w in state.get("weather", [])}
    acts = state.get("activities", [])
    feedback = state.get("feedback")

    n_days = req.nights + 1
    ctx = {
        "trip": req.model_dump(exclude={"origin_iata", "destination_iata"}),
        "days_context": [
            {"date": (req.start + timedelta(days=i)).isoformat(),
             "weather": weather.get((req.start + timedelta(days=i)).isoformat())}
            for i in range(n_days)
        ],
        "flight": {k: flights[sel["flight_id"]][k] for k in ("airline", "stops", "price")} if sel and sel["flight_id"] in flights else None,
        "hotel": hotel["name"] if hotel else None,
        "candidate_places": [{"name": a["name"], "category": a["category"]} for a in acts],
        "feedback": feedback,
        "previous_plan": state.get("plan") if feedback else None,
    }
    import json

    plan: TripPlan = await structured_llm(TripPlan).ainvoke(
        [SystemMessage(content=COMPOSE_PROMPT), HumanMessage(content=json.dumps(ctx, default=str))]
    )
    warns: list[str] = []

    # Ground the LLM output: real dates, real coordinates (never trust LLM-produced lat/lon).
    by_name = {a["name"].lower(): a for a in acts}
    if hotel and hotel.get("lat") and hotel.get("lon"):
        by_name[hotel["name"].lower()] = hotel
    for i, day in enumerate(plan.days[:n_days]):
        day.date = (req.start + timedelta(days=i)).isoformat()
    if len(plan.days) != n_days:
        warns.append(f"Itinerary has {len(plan.days)} days for a {n_days}-day trip.")
    for day in plan.days:
        for item in day.items:
            key = (item.place or "").lower()
            hit = by_name.get(key) or (by_name.get(m[0]) if (m := difflib.get_close_matches(key, by_name, 1, 0.8)) else None)
            item.lat, item.lon = (hit["lat"], hit["lon"]) if hit else (None, None)
            if not hit:
                item.place = None
    if plan.local_currency and plan.local_currency.upper() != req.currency:
        plan.exchange_rate = await _try(get_rate(req.currency, plan.local_currency.upper()), "Exchange rate", warns)
    emit("compose", "done", f"{len(plan.days)}-day itinerary")
    return {"plan": plan.model_dump(), "warnings": warns}


def approve(state: TravelState):
    """Human-in-the-loop: the user approves the plan or sends feedback for a revision."""
    decision = interrupt({"type": "approval", "plan": state["plan"], "selection": state.get("selection")})
    if isinstance(decision, dict) and decision.get("approved"):
        return {"feedback": None}
    text = decision.get("feedback") if isinstance(decision, dict) else str(decision)
    return {"feedback": text or "Please improve the plan."}


def route_after_approve(state: TravelState) -> str:
    return "compose" if state.get("feedback") else END


def build_graph(checkpointer):
    b = StateGraph(TravelState)
    b.add_node("parse", parse_request)
    b.add_node("clarify", clarify)
    b.add_node("prepare", prepare)
    b.add_node("flights", flights_node)
    b.add_node("hotels", hotels_node)
    b.add_node("activities", activities_node)
    b.add_node("weather", weather_node)
    b.add_node("optimize", optimize_node)
    b.add_node("compose", compose_node)
    b.add_node("approve", approve)

    b.add_edge(START, "parse")
    b.add_conditional_edges("parse", route_after_parse, ["clarify", "prepare"])
    b.add_edge("clarify", "parse")
    for name in PARALLEL:
        b.add_edge("prepare", name)  # fan-out: all four run in the same superstep
    b.add_edge(PARALLEL, "optimize")  # fan-in: waits for every branch
    b.add_edge("optimize", "compose")
    b.add_edge("compose", "approve")
    b.add_conditional_edges("approve", route_after_approve, ["compose", END])
    return b.compile(checkpointer=checkpointer)
