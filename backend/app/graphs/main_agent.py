from deepagents import create_deep_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

SYSTEM_PROMPT = (
    "When delegating with the `task` tool, ALWAYS provide both `subagent_type` "
    "and `description` (a one-sentence brief of what the sub-agent should do).\n"
    "When a tool returns an artifact (table or image), the UI already renders "
    "it as a card below your message. DO NOT paste the artifact as a markdown "
    "table or describe the image pixel-by-pixel — the user sees it directly. "
    'Reference it in prose ("see the table above", "see the chart above") '
    "or call out a few notable rows/values, and never invent placeholder rows "
    "like `...`.\n"
    "To process or plot data from a previous tool's table artifact, call "
    '`python_exec` and inside it call `read_artifact("art_…")` (with the '
    "bare id you saw in the prior tool summary). Tables come back as a pandas "
    "DataFrame — never `pd.read_csv` on an `art_…` path; those files do not "
    "exist. End plotting scripts with `out_image(plt.gcf(), title='…')` (or "
    "just `out_image()`); don't embed plots as markdown.\n"
    "When you need a table artifact from a DataFrame, call "
    '`out(df.reset_index().to_dict("records"))` — `out(df)` falls through to '
    "a text artifact (its repr), which is NOT a table.\n"
    "`read_table_summary` only accepts table artifacts. Before calling it, "
    "confirm the id you have is a table (the prior tool summary starts with "
    "`table …`); never call it on a `text` or `image` artifact.\n"
    "Sub-agents (returned via the `task` tool) end their reply with a line "
    "like `artifact_id=art_…; columns=…`. When you need to process that "
    "result, parse the id from that line — never invent an id, and never use "
    "a column name that isn't in the listed columns."
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
                "Run the final query via sql_query — its result is a table artifact the parent can read or chart via python_exec. "
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
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.google_api_key,
        temperature=settings.temperature,
        top_p=settings.top_p,
        top_k=settings.top_k,
    )
