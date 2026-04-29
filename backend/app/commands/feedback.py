from dataclasses import dataclass

from app.commands.base import CommandContext, SubagentResult

FEEDBACK_PROMPT = (
    "You are a feedback intake assistant. The user invoked `/feedback` to "
    "report a bug, request a feature, or leave a note. Your job is to "
    "produce a polished GitLab issue.\n\n"
    "Workflow — follow exactly:\n"
    "1. Inspect the user's text. If it is concrete enough that a developer "
    "could act on it (clear what / where / what was expected), skip to step 3.\n"
    "2. Otherwise ask AT MOST 2 short clarifying questions via the `quiz` "
    "tool (e.g. one about scope, one about severity). After 2 questions, "
    "proceed even if details are still thin.\n"
    "3. Call `gather_feedback_metadata` exactly once.\n"
    "4. Draft an issue:\n"
    "   - title: short imperative (max ~80 chars).\n"
    "   - description (Markdown):\n"
    "     ## Summary\n"
    "     <1-2 sentence rewrite of the user's report — clean grammar, "
    "neutral tone, preserve their meaning>.\n"
    "     ## User's original report\n"
    "     > <verbatim user text + any quiz answers>\n"
    "     ## Steps to reproduce / expected vs actual\n"
    "     <fill in if known, otherwise omit>\n"
    "     ---\n"
    "     **Reporter:** {reporter_email}\n"
    "     **Session:** {session_id}\n"
    "     **App version:** {app_version} ({git_sha})\n"
    "     **Browser:** {user_agent}\n"
    "     **Langfuse trace:** {langfuse_trace_url}\n"
    "5. Show the draft inline (title + description) and call `quiz` with a "
    "short confirmation prompt and exactly three options in the user's "
    "language: submit, edit description, and cancel.\n"
    "6. If the user chooses the submit option → call "
    "`submit_feedback_issue(title, description)` and reply with the returned "
    "`web_url`. If the user chooses the edit-description option → wait for "
    "the user's edited text in the next turn, then re-confirm. If the user "
    "chooses the cancel option → stop without submitting.\n\n"
    "Rules: do NOT call `submit_feedback_issue` before user confirmation. "
    "Do NOT invent metadata; use only what `gather_feedback_metadata` "
    "returns. Respond in the user's language."
)


@dataclass
class FeedbackCommand:
    name: str = "feedback"
    description: str = (
        "Report a bug or request — opens a GitLab issue with technical context attached."
    )
    arg_hint: str = "<your feedback>"

    async def handle(self, *, arg: str, ctx: CommandContext) -> SubagentResult:
        text = arg.strip()
        directive = (
            "The user invoked `/feedback`. Delegate to the `feedback-agent` "
            "subagent via the `task` tool with this exact `description`:\n\n"
            f"{text}"
            if text
            else "(no text provided — ask the user what the feedback is about)"
        )
        return SubagentResult(
            subagent={
                "name": "feedback-agent",
                "description": "Collects feedback context and creates a GitLab issue.",
                "system_prompt": FEEDBACK_PROMPT,
                "tools": [
                    "gather_feedback_metadata",
                    "submit_feedback_issue",
                    "quiz",
                ],
            },
            user_message=directive,
            tool_names=["gather_feedback_metadata", "submit_feedback_issue", "quiz"],
        )


command = FeedbackCommand()
