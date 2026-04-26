from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.config import get_settings
from app.graphs.main_agent import build_gemini_llm, build_ollama_llm


def resolve_llm(state, model: str) -> BaseChatModel:
    cache: dict = state.llm_cache
    llm = cache.get(model)
    if llm is None:
        settings = get_settings()
        if model.startswith("gemini"):
            llm = build_gemini_llm(settings, model=model)
        else:
            llm = build_ollama_llm(settings, model=model)
        cache[model] = llm
    return llm
