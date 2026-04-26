from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from deepagents import create_deep_agent

SYSTEM_PROMPT = "You are a helpful local assistant running on Gemma 4."


def build_agent(
    *,
    llm: BaseChatModel,
    tools: list[BaseTool],
    checkpointer,
    subagents: list[dict] | None = None,
):
    return create_deep_agent(
        model=llm,
        tools=tools,
        subagents=subagents or [],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


def build_ollama_llm(settings) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        num_ctx=settings.num_ctx,
        temperature=settings.temperature,
        top_p=settings.top_p,
        top_k=settings.top_k,
        reasoning=False,
        keep_alive=settings.keep_alive,
    )
