"""LLM client resolution for the Cognitive Fabric.

Returns provider-native clients (openai.OpenAI / anthropic.Anthropic) that
callers duck-type (`hasattr(client, "chat")` vs `"messages"`). Raises
LlmNotConfiguredError when no provider key/SDK is available so callers can
degrade gracefully instead of crashing.
"""

import os
from typing import Any, Optional

from cognitive_fabric.config import Settings
from cognitive_fabric.config import settings as default_settings


class LlmNotConfiguredError(RuntimeError):
    """Raised when an LLM client is requested but no provider is configured."""


def get_model_name(settings: Optional[Settings] = None) -> str:
    """Return the configured model name for the active provider."""
    settings = settings or default_settings
    if settings.llm_provider == "anthropic":
        return settings.anthropic_model
    return settings.openai_model


def get_llm_client(settings: Optional[Settings] = None) -> Any:
    """Resolve a provider-native LLM client.

    Raises:
        LlmNotConfiguredError: if the provider's API key is missing or its SDK
            cannot be imported.
    """
    settings = settings or default_settings
    provider = settings.llm_provider

    if provider == "anthropic":
        if not (settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")):
            raise LlmNotConfiguredError("ANTHROPIC_API_KEY is not set")
        try:
            from anthropic import Anthropic
        except Exception as e:  # pragma: no cover - SDK availability guard
            raise LlmNotConfiguredError(f"anthropic SDK unavailable: {e}") from e
        kwargs = (
            {"api_key": settings.anthropic_api_key}
            if settings.anthropic_api_key
            else {}
        )
        return Anthropic(**kwargs)

    # default: openai
    if not (settings.openai_api_key or os.environ.get("OPENAI_API_KEY")):
        raise LlmNotConfiguredError("OPENAI_API_KEY is not set")
    try:
        from openai import OpenAI
    except Exception as e:  # pragma: no cover - SDK availability guard
        raise LlmNotConfiguredError(f"openai SDK unavailable: {e}") from e
    kwargs = {"api_key": settings.openai_api_key} if settings.openai_api_key else {}
    return OpenAI(**kwargs)
