"""Vendored `append_to_system_message` (originally in `deepagents.middleware._utils`).

Kept local so middleware code does not depend on deepagents' private API.
"""

from __future__ import annotations

from langchain_core.messages import ContentBlock, SystemMessage


def append_to_system_message(
    system_message: SystemMessage | None,
    text: str,
) -> SystemMessage:
    new_content: list[ContentBlock] = list(system_message.content_blocks) if system_message else []
    if new_content:
        text = f"\n\n{text}"
    new_content.append({"type": "text", "text": text})
    return SystemMessage(content_blocks=new_content)
