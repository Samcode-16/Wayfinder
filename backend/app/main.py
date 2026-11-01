import json
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from pydantic import BaseModel

from .config import settings
from .graph import build_graph
from .llm import configured_providers


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
    if body.resume is not None:
        graph_input: Any = Command(resume=body.resume)
    elif body.message:
        graph_input = {"messages": [HumanMessage(content=body.message)]}
    else:
        raise HTTPException(400, "Provide `message` or `resume`.")
    thread_id = body.thread_id or str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    graph = request.app.state.graph

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
