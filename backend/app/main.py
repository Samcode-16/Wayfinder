import json
import re
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from .config import settings
from .graph import build_graph
from .llm import configured_providers
from .schemas import FlightOption, HotelOption


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSqliteSaver.from_conn_string(settings.db_path) as saver:
        app.state.graph = build_graph(saver)
        yield


app = FastAPI(title="AI Travel Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


class ChatIn(BaseModel):
    thread_id: str | None = None
    message: str | None = None  # a new user message
    resume: Any | None = None  # answer to a pending interrupt (clarification text or approval dict)
    select: dict | None = None  # optional explicit selection: {"flight_id": "...", "hotel_id": "..."}


def sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "llm_providers": configured_providers(),
        "live_travel_data": bool(settings.serpapi_api_key),
        "geoapify_api_key": settings.geoapify_api_key,
    }


@app.post("/api/chat")
async def chat(body: ChatIn, request: Request):
    """Streams Server-Sent Events: thread | step | update | interrupt | error | done."""
    thread_id = body.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    graph = request.app.state.graph

    resume_payload = body.resume if body.resume is not None else body.select

    snap = await graph.aget_state(config)
    has_interrupt = any(t.interrupts for t in snap.tasks) if snap else False

    if resume_payload is not None:
        if has_interrupt:
            graph_input: Any = Command(resume=resume_payload)
        elif snap and snap.values:
            # Re-plan/re-price on an existing thread where interrupt has completed
            flight_id = resume_payload.get("flight_id") or resume_payload.get("select_flight") if isinstance(resume_payload, dict) else None
            hotel_id = resume_payload.get("hotel_id") or resume_payload.get("select_hotel") if isinstance(resume_payload, dict) else None
            if not flight_id and not hotel_id and isinstance(resume_payload, dict) and isinstance(resume_payload.get("select"), dict):
                flight_id = resume_payload["select"].get("flight_id")
                hotel_id = resume_payload["select"].get("hotel_id")

            cur_sel = snap.values.get("selection") or {}
            target_fid = flight_id or cur_sel.get("flight_id")
            target_hid = hotel_id or cur_sel.get("hotel_id")

            flights_dict = {f["id"]: FlightOption(**f) for f in snap.values.get("flights", [])}
            hotels_dict = {h["id"]: HotelOption(**h) for h in snap.values.get("hotels", [])}
            f_obj = flights_dict.get(target_fid)
            h_obj = hotels_dict.get(target_hid)

            if f_obj and h_obj:
                from .graph import _req
                from .optimizer import price_selection
                req = _req(snap.values)
                fx = snap.values.get("fx", 1.0) or 1.0
                daily_spend = settings.daily_spend_usd_per_person * fx
                notes = []
                if flight_id and flight_id != cur_sel.get("flight_id"):
                    notes.append(f"Traveler selected {f_obj.airline} flight.")
                if hotel_id and hotel_id != cur_sel.get("hotel_id"):
                    notes.append(f"Traveler selected {h_obj.name}.")
                new_sel = price_selection(f_obj, h_obj, req, daily_spend, notes=notes)
                fb = f"Traveler switched to {h_obj.name if hotel_id else ''} {f_obj.airline if flight_id else ''}. Update the itinerary accordingly."
                await graph.aupdate_state(config, {"selection": new_sel.model_dump(), "feedback": fb}, as_node="approve")
                graph_input = None
            else:
                fb = resume_payload.get("feedback") if isinstance(resume_payload, dict) else str(resume_payload)
                await graph.aupdate_state(config, {"feedback": fb}, as_node="approve")
                graph_input = None
        else:
            graph_input = Command(resume=resume_payload)
    elif body.message:
        msg_text = body.message.strip()
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", msg_text)
        is_email_request = bool(email_match or any(w in msg_text.lower() for w in ["email", "mail", "send to"]))

        if is_email_request and snap and snap.values and snap.values.get("plan"):
            if email_match:
                extracted_email = email_match.group(0)
                from .tools.email import send_itinerary_email
                trip_data = {
                    "plan": snap.values.get("plan"),
                    "request": snap.values.get("request"),
                    "selection": snap.values.get("selection"),
                    "flights": snap.values.get("flights", []),
                    "hotels": snap.values.get("hotels", []),
                }
                res = await send_itinerary_email(extracted_email, trip_data)

                async def email_events():
                    yield sse("thread", {"thread_id": thread_id})
                    msg = f"✉️ {res['message']}"
                    yield sse("interrupt", {"type": "email_confirmation", "message": msg, "email": extracted_email})
                    yield sse("done", {})

                return StreamingResponse(email_events(), media_type="text/event-stream",
                                         headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
            else:
                async def ask_email_events():
                    yield sse("thread", {"thread_id": thread_id})
                    yield sse("interrupt", {"type": "ask_email", "message": "What email address should I send your itinerary to?"})
                    yield sse("done", {})

                return StreamingResponse(ask_email_events(), media_type="text/event-stream",
                                         headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

        graph_input = {"messages": [HumanMessage(content=body.message)]}
    else:
        raise HTTPException(400, "Provide `message`, `resume`, or `select`.")

    async def events():
        yield sse("thread", {"thread_id": thread_id})
        try:
            async for mode, chunk in graph.astream(graph_input, config, stream_mode=["updates", "custom"]):
                if mode == "custom":
                    yield sse("step", chunk)
                    continue
                for node, out in chunk.items():
                    if node == "__interrupt__":
                        for it in out:
                            yield sse("interrupt", it.value)
                    elif isinstance(out, dict):
                        data = {k: v for k, v in out.items() if k != "messages"}
                        if data:
                            yield sse("update", {"node": node, "data": data})
        except Exception as e:
            yield sse("error", {"message": f"{type(e).__name__}: {e}"})
        yield sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str, request: Request):
    """Restore a conversation after a page reload (state is persisted in SQLite)."""
    snap = await request.app.state.graph.aget_state({"configurable": {"thread_id": thread_id}})
    if not snap.values:
        raise HTTPException(404, "Unknown thread")
    values = {k: v for k, v in snap.values.items() if k != "messages"}
    pending = [i.value for t in snap.tasks for i in t.interrupts]
    return {"state": values, "pending_interrupt": pending[0] if pending else None}


class EmailIn(BaseModel):
    email: str
    thread_id: str | None = None
    plan: dict | None = None
    request: dict | None = None
    selection: dict | None = None
    flights: list[dict] = Field(default_factory=list)
    hotels: list[dict] = Field(default_factory=list)


@app.post("/api/email")
async def email_itinerary(body: EmailIn, request: Request):
    """Sends the trip itinerary to the customer's email address."""
    email = body.email.strip()
    from .tools.email import is_valid_email, send_itinerary_email

    if not is_valid_email(email):
        raise HTTPException(400, f"'{email}' is not a valid email address.")

    trip_data = {
        "plan": body.plan,
        "request": body.request,
        "selection": body.selection,
        "flights": body.flights,
        "hotels": body.hotels,
    }

    if not trip_data["plan"] and body.thread_id:
        snap = await request.app.state.graph.aget_state({"configurable": {"thread_id": body.thread_id}})
        if snap and snap.values:
            trip_data["plan"] = snap.values.get("plan")
            trip_data["request"] = snap.values.get("request")
            trip_data["selection"] = snap.values.get("selection")
            trip_data["flights"] = snap.values.get("flights", [])
            trip_data["hotels"] = snap.values.get("hotels", [])

    if not trip_data["plan"]:
        raise HTTPException(400, "No itinerary plan found to email.")

    res = await send_itinerary_email(email, trip_data)
    if not res.get("ok"):
        raise HTTPException(500, res.get("message", "Failed to send email."))
    return res
