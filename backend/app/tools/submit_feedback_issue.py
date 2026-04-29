from langchain_core.tools import tool

from app.integrations import gitlab


@tool
async def submit_feedback_issue(title: str, description: str) -> dict:
    """Create a GitLab issue with the given title and description (Markdown).

    Returns `{web_url, iid}` on success. Call only after the user has confirmed
    the draft via `quiz`. Includes label `feedback` automatically.
    """
    res = await gitlab.create_issue(title=title, description=description, labels=["feedback"])
    return {"web_url": res.get("web_url"), "iid": res.get("iid")}
