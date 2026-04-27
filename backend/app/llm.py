from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from loguru import logger

from app.config import get_settings
from app.graphs.main_agent import build_gemini_llm, build_ollama_llm

_LOCAL_CONTEXT_CAP = 16_384


def context_max_tokens(llm: BaseChatModel) -> int | None:
    # ChatOllama exposes `num_ctx`; we treat that presence as the local-model
    # signal and cap displayed context at 16k regardless of the configured
    # value, since small local models lose recall well before then.
    num_ctx = getattr(llm, "num_ctx", None)
    if isinstance(num_ctx, int) and num_ctx > 0:
        return min(num_ctx, _LOCAL_CONTEXT_CAP)
    profile = getattr(llm, "profile", None)
    if isinstance(profile, dict):
        n = profile.get("max_input_tokens")
        if isinstance(n, int) and n > 0:
            return n
    return get_settings().num_ctx or None


def resolve_llm(state, model: str) -> BaseChatModel:
    cache: dict = state.llm_cache
    llm = cache.get(model)
    if llm is None:
        settings = get_settings()
        if model.startswith("gemini"):
            if not settings.google_api_key:
                # Surface a missing key up-front; ChatGoogleGenerativeAI
                # otherwise dies mid-stream with an opaque auth error.
                logger.warning(f"resolve_llm: gemini model={model!r} but google_api_key is empty")
            logger.info(f"resolve_llm: provider=gemini model={model!r} (cache miss)")
            llm = build_gemini_llm(settings, model=model)
        else:
            logger.info(
                f"resolve_llm: provider=ollama model={model!r} base_url={settings.ollama_base_url} "
                f"(cache miss)"
            )
            llm = build_ollama_llm(settings, model=model)
        cache[model] = llm
    return llm
