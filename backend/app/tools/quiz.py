from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def quiz(question: str, options: list[str], allow_custom: bool = True) -> str:
    """Ask the user a multiple-choice question when you genuinely cannot proceed.

    Use sparingly: only when an ambiguous trade-off, missing requirement, or
    branching decision blocks progress and you can't reasonably guess. Provide
    2-4 short, distinct options. The user picks one or types a custom answer;
    the chosen text is returned to you as the tool result.
    """
    answer = interrupt(
        {
            "kind": "quiz",
            "question": question,
            "options": options,
            "allow_custom": allow_custom,
        }
    )
    return str(answer)
