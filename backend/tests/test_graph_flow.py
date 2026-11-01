"""End-to-end run of the real graph with a fake LLM: clarify -> parallel fan-out -> optimize -> compose -> approve."""
import asyncio
from datetime import date, timedelta

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import app.graph as g
from app.schemas import DayPlan, ItineraryItem, TripPlan, TripRequest

START = (date.today() + timedelta(days=60)).isoformat()
END = (date.today() + timedelta(days=64)).isoformat()


class FakeLLM:
    def __init__(self, schema):
        self.schema = schema
        self.calls = 0

    async def ainvoke(self, messages):
        if self.schema is TripRequest:
            text = " ".join(m.content for m in messages if isinstance(m, HumanMessage)).lower()
            has_dest = "amsterdam" in text
            return TripRequest(origin="Madrid", origin_iata="MAD", destination="Amsterdam" if has_dest else None,
                               destination_iata="AMS" if has_dest else None, start_date=START, end_date=END,
                               travelers=2, budget=4000, currency="EUR")
        feedback = "feedback" in messages[-1].content and '"feedback": null' not in messages[-1].content
        days = [DayPlan(date="1999-01-01", theme="Canals" + (" (revised)" if feedback else ""),
                        items=[ItineraryItem(time_of_day="morning", title="Walk", description="x", place="Nowhere")])
                for _ in range(5)]
        return TripPlan(title="Amsterdam", summary="s", days=days, local_currency="EUR")


def test_full_flow(monkeypatch):
    monkeypatch.setattr(g, "structured_llm", lambda schema: FakeLLM(schema))
    graph = g.build_graph(InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}

    async def run():
        r1 = await graph.ainvoke({"messages": [HumanMessage("Trip from Madrid next month")]}, cfg)
        r2 = await graph.ainvoke(Command(resume="Amsterdam please"), cfg)
        r3 = await graph.ainvoke(Command(resume={"approved": False, "feedback": "more food spots"}), cfg)
        r4 = await graph.ainvoke(Command(resume={"approved": True}), cfg)
        return r1, r2, r3, r4

    r1, r2, r3, r4 = asyncio.run(run())

    # 1) missing destination -> graph paused with a clarification question
    assert r1["__interrupt__"][0].value["type"] == "clarify"
    assert r1["__interrupt__"][0].value["missing"] == ["destination"]
    # 2) answered -> all parallel branches ran, trip priced, plan composed, now awaiting approval
    assert r2["__interrupt__"][0].value["type"] == "approval"
    assert len(r2["flights"]) > 0 and len(r2["hotels"]) > 0
    assert r2["selection"]["total"] > 0
    plan = r2["plan"]
    assert [d["date"] for d in plan["days"]][0] == START and len(plan["days"]) == 5  # dates grounded
    assert plan["days"][0]["items"][0]["place"] is None  # hallucinated place stripped
    assert any("demo" in w.lower() for w in r2["warnings"])
    # 3) feedback loop re-composes, 4) approval ends the run
    assert "revised" in r3["plan"]["days"][0]["theme"] and r3["__interrupt__"][0].value["type"] == "approval"
    assert "__interrupt__" not in r4
