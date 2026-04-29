from urllib.parse import quote

import httpx

from app.config import get_settings


async def create_issue(*, title: str, description: str, labels: list[str] | None = None) -> dict:
    settings = get_settings()
    if not (settings.gitlab_url and settings.gitlab_token and settings.gitlab_project_id):
        raise RuntimeError("GitLab not configured: set GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT_ID")
    base = settings.gitlab_url.rstrip("/")
    project = quote(settings.gitlab_project_id, safe="")
    url = f"{base}/api/v4/projects/{project}/issues"
    payload: dict = {"title": title, "description": description}
    if labels:
        payload["labels"] = ",".join(labels)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            url,
            headers={"PRIVATE-TOKEN": settings.gitlab_token},
            json=payload,
        )
        r.raise_for_status()
        return r.json()
