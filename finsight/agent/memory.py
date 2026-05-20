"""Conversation memory — stores the rolling message window for the agent chat interface."""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConversationMemory:
    """
    Rolling window of conversation messages for the agent chat interface.
    Keeps the last `max_messages` turns (system prompt NOT stored here — injected at call time).
    """
    max_messages: int = 20
    _messages: list[dict] = field(default_factory=list, repr=False)

    def add_user(self, content: str) -> None:
        """Append a user turn."""
        self._append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        """Append an assistant turn."""
        self._append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_name: str, result: object) -> None:
        """Append a tool result as a user-role message so the LLM sees it."""
        serialised = json.dumps(result, default=str)
        self._append({
            "role": "user",
            "content": f"[Tool result: {tool_name}]\n{serialised}",
        })

    def get_messages(self, system_prompt: str) -> list[dict]:
        """Return the full message list with the system prompt prepended."""
        return [{"role": "system", "content": system_prompt}] + list(self._messages)

    def reset(self) -> None:
        """Clear the conversation — call this when starting a new session."""
        self._messages.clear()
        logger.debug("ConversationMemory reset")

    def __len__(self) -> int:
        return len(self._messages)

    def _append(self, message: dict) -> None:
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            # Drop oldest messages but never drop the first one if it's context-setting
            self._messages = self._messages[-self.max_messages:]
