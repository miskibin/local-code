from deepagents import create_deep_agent
from deepagents.backends.state import StateBackend
from deepagents.middleware.summarization import (
    SummarizationToolMiddleware,
    create_summarization_middleware,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

from app.middleware.skills_state import StateSkillsMiddleware
from app.middleware.tool_exclusion import ToolExclusionMiddleware
from app.skills_registry import SkillInfo
from app.tools.sql_subagent_query import schema_blob

_EXCLUDED_BUILTIN_TOOLS = frozenset(
    {"ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute"}
)


def _build_disabled_general_purpose_runnable():
    """Build a CompiledSubAgent that immediately returns a refusal message.

    Replaces deepagents' auto-injected `general-purpose` subagent so:
    1. The model can't actually do anything if it dispatches there — no
       FilesystemMiddleware, no `ls`/`grep`/`read_file`/etc. injected.
    2. There's no LLM call inside the subagent, so it can't go on a tangent.
    Deepagents recognises specs with a `runnable` key as pre-compiled and
    skips its own middleware-stack assembly entirely (subagents.py:485).
    """

    def _refuse(state):
        return {
            "messages": [
                AIMessage(
                    content=(
                        "general-purpose is disabled in this harness. "
                        "Use `sql-agent` for DB questions or call parent "
                        "tools directly."
                    )
                )
            ]
        }

    g = StateGraph(MessagesState)
    g.add_node("refuse", _refuse)
    g.add_edge(START, "refuse")
    g.add_edge("refuse", END)
    return g.compile()


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
    "`python_exec` is sandboxed: NO DB drivers (`sqlite3`, `sqlalchemy`, "
    "etc.), NO network (`requests`, `urllib`, `socket`), NO subprocess, NO "
    "project file access. For any SQL/DB question delegate to the "
    "`sql-agent` subagent — never try to query a DB from `python_exec`.\n"
    "`read_table_summary` only accepts table artifacts. Before calling it, "
    "confirm the id you have is a table (the prior tool summary starts with "
    "`table …`); never call it on a `text` or `image` artifact.\n"
    "Sub-agents (returned via the `task` tool) end their reply with an "
    "`artifact_id=art_…; columns=…` line followed by a small markdown head "
    "table preview. Parse the id from that line (never invent an id, never "
    "use a column name not listed) and trust the preview rows for quick "
    "answers — call `read_table_summary` only if you need more rows or "
    "column statistics.\n"
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
    custom_instructions: str = "",
):
    # The `middleware` arg below only wraps the top-level agent. Subagents
    # dispatched through `task` build their own model-call stack and would
    # otherwise inherit the parent tool roster — including built-ins like
    # `ls`/`grep` that we exclude here. Without the per-subagent middleware
    # a small model can spiral into thousands of `ls` calls before the parent
    # ever sees a result.
    # deepagents auto-injects a `general-purpose` subagent unless one with that
    # name is already in the list (graph.py:546). We replace it with a
    # CompiledSubAgent (`runnable` key form) so deepagents skips its default
    # middleware stack entirely (subagents.py:485) — no Filesystem tools, no
    # LLM call, just a refusal. sql-agent + direct tools cover our scope.
    disabled_general_purpose = {
        "name": "general-purpose",
        "description": (
            "DISABLED. Do NOT call. Delegate DB/analysis to `sql-agent`; "
            "for everything else call parent tools directly."
        ),
        "runnable": _build_disabled_general_purpose_runnable(),
    }
    # Subagents always run with the full exclusion (skills are top-level only).
    # write_todos is a top-level planning tool only — subagents must not create
    # their own plan cards (causes duplicate Plan blocks in the UI).
    subagent_excluded = _EXCLUDED_BUILTIN_TOOLS | {"write_todos"}

    def _with_subagent_exclusion(spec: dict) -> dict:
        return {
            **spec,
            "middleware": [
                *list(spec.get("middleware") or []),
                ToolExclusionMiddleware(excluded=subagent_excluded),
            ],
        }

    prepared_subagents = [disabled_general_purpose] + [
        _with_subagent_exclusion(spec) for spec in (subagents or [])
    ]

    # Top-level agent: when skills enabled, allow read_file so the model can
    # load skill bodies that StateSkillsMiddleware seeded into state["files"].
    parent_excluded = _EXCLUDED_BUILTIN_TOOLS
    parent_middleware: list = []
    if enabled_skills:
        parent_excluded = parent_excluded - {"read_file"}
        parent_middleware.append(StateSkillsMiddleware(skills=enabled_skills))
    parent_middleware.insert(0, ToolExclusionMiddleware(excluded=parent_excluded))

    # Add the manual `compact_conversation` tool. `create_deep_agent` already
    # injects a SummarizationMiddleware for auto-compaction; this exposes the
    # same engine to the model (shared `_summarization_event` state key) so it
    # can compact on demand. We instantiate our own summarization config purely
    # as a holder — only the tool middleware is registered to avoid the
    # langchain factory's "duplicate middleware" guard.
    summ_config = create_summarization_middleware(llm, StateBackend())
    parent_middleware.append(SummarizationToolMiddleware(summ_config))

    prompt = SYSTEM_PROMPT
    if custom_instructions.strip():
        prompt = (
            SYSTEM_PROMPT
            + "\n\n## User-provided custom instructions\n"
            + "(From the user's Settings → Instructions tab. Treat as additional "
            + "standing rules unless they conflict with the rules above.)\n\n"
            + custom_instructions.strip()
        )

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        subagents=prepared_subagents,
        system_prompt=prompt,
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
                "Your final reply MUST include the small `head:` markdown table "
                "from the sql_query summary (so the parent can answer without an "
                "extra read_table_summary round-trip), and MUST end with the "
                "artifact-id trailer on its own line. Exact shape:\n"
                "  <prose, one or two sentences>\n"
                "  <copy the `head:` markdown table verbatim from the sql_query summary>\n"
                "  artifact_id=<bare id from the sql_query summary>; columns=<comma-separated column names>\n"
                "Example:\n"
                "  Top customers by spend.\n"
                "  | FirstName | LastName | TotalSpend |\n"
                "  |:----------|:---------|-----------:|\n"
                "  | Helena    | Holý     |      49.62 |\n"
                "  artifact_id=art_754c2be1b408; columns=FirstName,LastName,TotalSpend\n"
                "Copy the id verbatim from the sql_query summary (the token before ` · `). "
                "The artifact_id line MUST be the last non-empty line. "
                "Never invent ids or rows; never wrap in brackets or quotes. "
                "If the result has no rows, omit the head table.\n"
                "On `sql_query` error: do NOT re-issue the same SQL. Read the error, "
                "change the query (fix syntax, drop offending tokens like markdown links, "
                "simplify), or stop and return one sentence explaining why it cannot run. "
                "Never emit the same SQL twice in a row."
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
