from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

SYSTEM_PROMPT = (
    "When delegating with the `task` tool, ALWAYS provide both `subagent_type` "
    "and `description` (a one-sentence brief of what the sub-agent should do).\n"
    "When a tool returns an artifact (table or chart), the UI already renders "
    "it as a card below your message. DO NOT paste the artifact as a markdown "
    "table or chart in your reply — the user sees it directly. Reference it in "
    "prose (\"see the table above\") or call out a few notable rows/values, "
    "and never invent placeholder rows like `...`.\n"
    "Tool summaries that begin with a token like `art_abc123def456 · …` are "
    "telling you the artifact id. To plot or operate on that artifact, copy "
    "ONLY that bare id (e.g. `art_abc123def456`) into the next tool's "
    "`artifact_id` argument — never `[artifact_id=…]`, never the literal "
    "string \"artifact_id\", never quote the id.\n"
    "Sub-agents (returned via the `task` tool) end their reply with a line "
    "like `artifact_id=art_…; columns=…`. When you need to chart or process "
    "that result, parse the id from that line — never invent an id, and never "
    "use a column name that isn't in the listed columns."
)


def build_agent(
    *,
    llm: BaseChatModel,
    tools: list[BaseTool],
    checkpointer,
    subagents: list[dict] | None = None,
):
    return create_deep_agent(
        model=llm,
        tools=tools,
        subagents=subagents or [],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def default_subagents() -> list[dict]:
    return [
        {
            "name": "research-agent",
            "description": "Use for in-depth research that needs its own context window.",
            "system_prompt": "You are a thorough researcher. Use web_fetch liberally. Return a tight, sourced summary.",
            "tools": ["web_fetch"],
        },
        {
            "name": "sql-agent",
            "description": "Use for SQL exploration over the bundled Chinook DB. The agent inspects the schema and returns a table artifact (referenced by id) for the parent to consume.",
            "system_prompt": (
                "You are a careful SQL analyst working over a SQLite Chinook DB. "
                "Always start by calling sql_db_list_tables, then sql_db_schema for the relevant tables. "
                "Never SELECT *. Always cap with LIMIT 200. "
                "Run the final query via sql_query — its result is a table artifact the parent can chart or filter further. "
                "The UI renders that artifact as a card; in your final reply do NOT paste a markdown table, "
                "and never invent placeholder rows like `...`. Describe the result in one or two sentences.\n"
                "CRITICAL — the parent agent cannot see the inner tool summaries. "
                "Your final reply MUST end with a single line in this exact shape:\n"
                "  artifact_id=<bare id from the sql_query summary>; columns=<comma-separated column names>\n"
                "Example: `artifact_id=art_754c2be1b408; columns=FirstName,LastName,TotalSpend`. "
                "Copy the id verbatim from the sql_query summary (the token before ` · `). "
                "Never invent ids; never wrap them in brackets or quotes."
            ),
            "tools": ["sql_db_list_tables", "sql_db_schema", "sql_query"],
        },
    ]


def build_ollama_llm(settings, *, model: str) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model,
        base_url=settings.ollama_base_url,
        num_ctx=settings.num_ctx,
        temperature=settings.temperature,
        top_p=settings.top_p,
        top_k=settings.top_k,
        reasoning=False,
        keep_alive=settings.keep_alive,
    )


def build_gemini_llm(settings, *, model: str) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.google_api_key,
        temperature=settings.temperature,
        top_p=settings.top_p,
        top_k=settings.top_k,
    )
