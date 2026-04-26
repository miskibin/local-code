def test_default_subagents_includes_research_agent():
    from app.graphs.main_agent import default_subagents

    subs = default_subagents()
    names = {s["name"] for s in subs}
    assert "research-agent" in names
    research = next(s for s in subs if s["name"] == "research-agent")
    assert "web_fetch" in research["tools"]
