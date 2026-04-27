from deepagents import create_deep_agent
from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from app.middleware.skills_state import StateSkillsMiddleware
from app.skills_registry import SkillInfo
from app.tools.sql_subagent_query import schema_blob

_EXCLUDED_BUILTIN_TOOLS = frozenset(
    {"ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute"}
)

SYSTEM_PROMPT = (
    "When delegating with the `task` tool, ALWAYS provide both `subagent_type` "
    "and `description` (a one-sentence brief of what the sub-agent should do).\n"
    "For any SQL or Chinook-DB question (sales, tracks, customers, invoices, "
    "genres, employees, etc.), delegate to the `sql-agent` subagent via the "
    "`task` tool — do NOT call `sql_query` yourself. Parse the "
    "`artifact_id=…; columns=…` line from the subagent's reply and use that id "
    "for any follow-up `python_exec` / charting / `read_table_summary` calls.\n"
    "Artifact visibility: tool-produced artifacts are HIDDEN from the chat by "
    "default. The user only sees a small chip on the tool call. To surface an "
    "artifact inline in your final reply, mention it with markdown link syntax "
    "`[short label](artifact:<artifact_id>)` — e.g. "
    "`see the [revenue chart](artifact:art_754c2be1b408)`. Use the bare id "
    "from the prior tool summary; do not wrap in quotes or brackets. Mention "
    "sparingly: only artifacts the user should look at right now. Never paste "
    "the artifact as a markdown table or describe an image pixel-by-pixel, "
    "and never invent placeholder rows like `...`.\n"
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
    "a column name that isn't in the listed columns.\n"
    "If a skill in the available-skills list matches the user's request, you "
    "MAY load it with `read_file` for deeper guidance — the skill contains "
    "extra recipes and worked examples, not core rules."
)


def build_agent(
    *,
    llm: BaseChatModel,
    tools: list[BaseTool],
    checkpointer,
    subagents: list[dict] | None = None,
    enabled_skills: list[SkillInfo] | None = None,
):
    # The `middleware` arg below only wraps the top-level agent. Subagents
    # dispatched through `task` build their own model-call stack and would
    # otherwise inherit the parent tool roster — including built-ins like
    # `ls`/`grep` that we exclude here. Without the per-subagent middleware
    # a small model can spiral into thousands of `ls` calls before the parent
    # ever sees a result.
    # deepagents auto-injects a `general-purpose` subagent unless one with that
    # name is already in the list (graph.py:546). Override with a stub so the
    # parent never delegates to it — sql-agent + direct tools cover our scope.
    stub_general_purpose = {
        "name": "general-purpose",
        "description": "Do not use. Call tools directly or delegate to sql-agent.",
        "system_prompt": "Reply only: 'Use sql-agent or call parent tools directly.'",
        "tools": [],
    }
    # Subagents always run with the full exclusion (skills are top-level only).
    subagent_excluded = _EXCLUDED_BUILTIN_TOOLS
    prepared_subagents = [stub_general_purpose] + [
        {
            **spec,
            "middleware": [
                *list(spec.get("middleware") or []),
                _ToolExclusionMiddleware(excluded=subagent_excluded),
            ],
        }
        for spec in (subagents or [])
    ]

    # Top-level agent: when skills enabled, allow read_file so the model can
    # load skill bodies that StateSkillsMiddleware seeded into state["files"].
    parent_excluded = _EXCLUDED_BUILTIN_TOOLS
    parent_middleware: list = []
    if enabled_skills:
        parent_excluded = parent_excluded - {"read_file"}
        parent_middleware.append(StateSkillsMiddleware(skills=enabled_skills))
    parent_middleware.insert(0, _ToolExclusionMiddleware(excluded=parent_excluded))

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        subagents=prepared_subagents,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        middleware=parent_middleware,
    )
    return agent.with_config({"recursion_limit": 100})


def default_subagents() -> list[dict]:
    return [
        {
            "name": "sql-agent",
            "description": "Use for SQL exploration over the bundled Chinook DB. Returns a table artifact (referenced by id) for the parent to consume.",
            "system_prompt": (
                "You are a careful SQL analyst working over a SQLite Chinook DB. "
                "Never SELECT *. Always cap with LIMIT 200. "
                "Run the final query via sql_query — its result is a table artifact the parent can read or chart via python_exec. "
                "The UI renders that artifact as a card; in your final reply do NOT paste a markdown table, "
                "and never invent placeholder rows like `...`. Describe the result in one or two sentences.\n"
                "Schema (authoritative — do not call discovery tools, do not invent columns):\n"
                f"{schema_blob()}\n"
                "CRITICAL — the parent agent cannot see the inner tool summaries. "
                "Your final reply MUST end with a single line in this exact shape:\n"
                "  artifact_id=<bare id from the sql_query summary>; columns=<comma-separated column names>\n"
                "Example: `artifact_id=art_754c2be1b408; columns=FirstName,LastName,TotalSpend`. "
                "Copy the id verbatim from the sql_query summary (the token before ` · `). "
                "Never invent ids; never wrap them in brackets or quotes."
            ),
            "tools": ["sql_query", "quiz"],
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
