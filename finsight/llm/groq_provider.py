"""Groq implementation of BaseLLMProvider — llama-3.3-70b (reasoning), llama-3.1-8b (fast)."""

import json
import logging
import os
import time
from collections.abc import AsyncIterator

from groq import AsyncGroq, Groq, RateLimitError

from .provider import BaseLLMProvider, LLMResponse, TokenUsage, ToolCall

logger = logging.getLogger(__name__)

_REASONING_MODEL = "llama-3.3-70b-versatile"
_FAST_MODEL = "llama-3.1-8b-instant"


class GroqProvider(BaseLLMProvider):
    """Groq-backed LLM provider using the OpenAI-compatible Groq API."""

    def __init__(self, role: str = "reasoning") -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set")
        model_env = "LLM_REASONING_MODEL" if role == "reasoning" else "LLM_FAST_MODEL"
        default = _REASONING_MODEL if role == "reasoning" else _FAST_MODEL
        self._model = os.getenv(model_env, default)
        self._client = Groq(api_key=api_key)
        self._async_client = AsyncGroq(api_key=api_key)

    def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        def _call():
            kwargs: dict = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            return self._client.chat.completions.create(**kwargs)

        resp = self._retry_groq(_call)
        msg = resp.choices[0].message

        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                ToolCall(
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in msg.tool_calls
            ]

        return LLMResponse(
            content=msg.content or "",
            model=resp.model,
            usage=TokenUsage(
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                total_tokens=resp.usage.total_tokens,
            ),
            tool_calls=tool_calls,
        )

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        stream = await self._async_client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def _retry_groq(self, func, retries: int = 4, base_delay: float = 2.0):
        """Retry with exponential backoff, respecting Groq's retry-after header on 429."""
        for attempt in range(retries):
            try:
                return func()
            except RateLimitError as exc:
                if attempt == retries - 1:
                    raise
                retry_after = _parse_retry_after(exc)
                wait = retry_after if retry_after else base_delay * (2 ** attempt)
                logger.warning("Groq rate limit hit — waiting %.1fs (attempt %d/%d)", wait, attempt + 1, retries)
                time.sleep(wait)
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt))


def _parse_retry_after(exc: RateLimitError) -> float | None:
    """Extract retry-after seconds from a Groq RateLimitError, if present."""
    try:
        headers = getattr(exc, "response", None) and exc.response.headers
        if headers and "retry-after" in headers:
            return float(headers["retry-after"])
    except Exception:
        pass
    return None
