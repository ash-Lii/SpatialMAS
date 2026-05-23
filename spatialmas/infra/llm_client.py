from __future__ import annotations

from langchain.chat_models import init_chat_model

from spatialmas.config import get_settings, require_llm_settings


def create_llm(temperature: float = 0):
    require_llm_settings()
    settings = get_settings()
    return init_chat_model(
        model=settings.model,
        model_provider="openai",
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base,
        temperature=temperature,
    )
