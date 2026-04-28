from langchain_core.tools import tool


@tool
def email_draft(
    to: str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    attachment_artifact_ids: list[str] | None = None,
) -> str:
    """Compose an email draft for the user to review and send manually.

    Use when the user asks for an email — follow-up, intro, recap, etc. The
    draft renders as a card in the assistant response; the user can copy or
    open it in their mail app. This tool does NOT send anything.

    Pass `body` as plain text with blank-line paragraph breaks. Keep `subject`
    short (under ~80 chars). `cc`/`bcc` are optional lists of addresses.

    The `From:` line is filled automatically from the logged-in user — do not
    pass or invent a sender address.

    To attach files, pass `attachment_artifact_ids`: a list of artifact IDs
    from prior tool results in this session (tables, images, text). The card
    will show attachment chips; clicking "Open in mail" downloads them so the
    user can attach in their mail app (mailto cannot carry attachments).
    """
    return f"Drafted email to {to}: {subject!r}"
