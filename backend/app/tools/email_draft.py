import json

from langchain_core.tools import tool


@tool
def email_draft(
    to: str,
    subject: str,
    body: str,
    from_address: str = "",
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> str:
    """Compose an email draft for the user to review and send manually.

    Use when the user asks for an email — follow-up, intro, recap, etc. The
    draft renders as a card the user can copy, mark sent, or discard. This
    tool does NOT send anything; sending happens in the user's mail app.

    Pass `body` as plain text with blank-line paragraph breaks. Keep `subject`
    short (under ~80 chars). `cc`/`bcc` are optional lists of addresses.
    """
    payload = {
        "to": to,
        "subject": subject,
        "body": body,
        "from": from_address,
        "cc": cc or [],
        "bcc": bcc or [],
    }
    return json.dumps(payload, ensure_ascii=False)
