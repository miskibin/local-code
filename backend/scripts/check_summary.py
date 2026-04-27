"""Manual e2e check: drive the agent with big conversation, see if auto-summary fires."""

from __future__ import annotations

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.config import get_settings
from app.graphs.main_agent import build_agent, build_ollama_llm
from app.skills_registry import discover_skills, filter_enabled


async def main() -> None:
    settings = get_settings()
    llm = build_ollama_llm(settings, model="gemma4:e4b")
    print(f"profile: {llm.profile}")
    print(f"num_ctx: {settings.num_ctx}")

    enabled_skills = filter_enabled(discover_skills(settings.skills_dir), {})
    checkpointer = MemorySaver()
    graph = build_agent(
        llm=llm,
        tools=[],
        checkpointer=checkpointer,
        subagents=[],
        enabled_skills=enabled_skills,
    )

    config = {"configurable": {"thread_id": "summary-test"}}

    # Force tokens past trigger: send one giant user message ~30k tokens of filler.
    big = "filler line. " * 12000  # ~36k tokens by approximate counter
    msgs = [HumanMessage(content=big), HumanMessage(content="say hi briefly")]

    # Mirror production: actually call stream_chat to verify the SSE emission.
    from app.streaming import stream_chat  # noqa: PLC0415

    print("invoking via stream_chat...")
    saw_summary_event = False
    n_events = 0
    async for sse in stream_chat(
        graph=graph,
        thread_id="summary-test",
        lc_messages=msgs,
        session_id="summary-test",
        context_max_tokens=settings.num_ctx,
        model_id="gemma4:e4b",
        checkpointer=checkpointer,
    ):
        n_events += 1
        if '"data-summary"' in sse:
            saw_summary_event = True
            print(f"  >>> data-summary SSE: {sse[:200]}")
    print(f"total SSE events: {n_events}")
    print(f"saw data-summary: {saw_summary_event}")

    # Final checkpoint inspection
    tup = await checkpointer.aget_tuple(config)
    if tup is None:
        print("no checkpoint persisted")
        return
    cv = tup.checkpoint.get("channel_values") or {}
    evt = cv.get("_summarization_event")
    print(f"\nfinal _summarization_event: {evt}")
    print(f"channel_values keys: {sorted(cv.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
