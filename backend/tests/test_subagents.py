def test_default_subagents_is_only_sql_agent(chinook_path):
    from app.graphs.main_agent import default_subagents

    subs = default_subagents()
    assert len(subs) == 1
    sql = subs[0]
    assert sql["name"] == "sql-agent"
    assert sql["tools"] == ["sql_query", "quiz"]


def test_sql_agent_system_prompt_bakes_chinook_schema(chinook_path):
    from app.graphs.main_agent import default_subagents

    prompt = default_subagents()[0]["system_prompt"]
    assert "CREATE TABLE" in prompt
    for table in ("Album", "Customer", "InvoiceLine"):
        assert table in prompt, f"expected {table!r} in baked schema"
    # Regression guard: discovery directive and tools must be gone.
    assert "sql_db_list_tables" not in prompt
    assert "sql_db_schema" not in prompt
