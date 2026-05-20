"""Provider selection — reads LLM_PROVIDER from env and returns the configured BaseLLMProvider."""

import os

from .provider import BaseLLMProvider


def get_llm(role: str = "reasoning") -> BaseLLMProvider:
    """Return the configured LLM provider. role is 'reasoning' (large) or 'fast' (small)."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider == "groq":
        from .groq_provider import GroqProvider
        return GroqProvider(role=role)
    if provider == "gemini":
        from .gemini_provider import GeminiProvider
        return GeminiProvider(role=role)
    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider!r}. Valid options: 'groq', 'gemini'"
    )
