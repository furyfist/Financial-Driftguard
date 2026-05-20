"""Provider-agnostic LLM interface used by all FinSight AI components."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
import time


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: TokenUsage
    tool_calls: list[ToolCall] | None = field(default=None)


class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers. Swap by changing LLM_PROVIDER env var."""

    def _retry(self, func, retries: int = 3, base_delay: float = 1.0):
        """Run func with exponential backoff — 1s, 2s, 4s between attempts."""
        for attempt in range(retries):
            try:
                return func()
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(base_delay * (2 ** attempt))

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send a chat completion request and return a structured response."""
        ...

    @abstractmethod
    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream a chat completion, yielding text chunks as they arrive."""
        ...
