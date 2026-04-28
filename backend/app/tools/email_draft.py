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
    draft renders as a card in the assistant response; the user can copy,
    mark sent, or open it in their mail app. This tool does NOT send anything.

    Pass `body` as plain text with blank-line paragraph breaks. Keep `subject`
    short (under ~80 chars). `cc`/`bcc` are optional lists of addresses.
    Always provide a `from_address` if the user has one — it appears as the
    From: field on the card.
    """
    return f"Drafted email to {to}: {subject!r}"
