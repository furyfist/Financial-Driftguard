"""Tests for the LLM abstraction layer — verifies the provider-agnostic contract."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from finsight.llm.provider import LLMResponse, TokenUsage, ToolCall


# ── Dataclass contract ────────────────────────────────────────────────────────

def test_llm_response_fields():
    usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    resp = LLMResponse(content="hello", model="test-model", usage=usage)
    assert resp.content == "hello"
    assert resp.model == "test-model"
    assert resp.tool_calls is None
    assert resp.usage.total_tokens == 30


def test_tool_call_fields():
    tc = ToolCall(name="my_tool", arguments={"x": 1})
    assert tc.name == "my_tool"
    assert tc.arguments["x"] == 1


# ── GroqProvider helpers ──────────────────────────────────────────────────────

def _groq_mock_response(content: str = "answer", tool_calls=None):
    usage = MagicMock()
    usage.prompt_tokens = 5
    usage.completion_tokens = 10
    usage.total_tokens = 15

    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = msg

    resp = MagicMock()
    resp.choices = [choice]
    resp.model = "llama-3.3-70b-versatile"
    resp.usage = usage
    return resp


# ── GroqProvider tests ────────────────────────────────────────────────────────

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
@patch("finsight.llm.groq_provider.AsyncGroq")
@patch("finsight.llm.groq_provider.Groq")
def test_groq_complete_returns_llm_response(mock_groq, mock_async_groq):
    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    mock_async_groq.return_value = MagicMock()
    mock_client.chat.completions.create.return_value = _groq_mock_response("hello")

    from finsight.llm.groq_provider import GroqProvider
    result = GroqProvider(role="reasoning").complete([{"role": "user", "content": "hi"}])

    assert isinstance(result, LLMResponse)
    assert result.content == "hello"
    assert result.tool_calls is None
    assert result.usage.total_tokens == 15


@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
@patch("finsight.llm.groq_provider.AsyncGroq")
@patch("finsight.llm.groq_provider.Groq")
def test_groq_complete_with_tool_calls(mock_groq, mock_async_groq):
    mock_tc = MagicMock()
    mock_tc.function.name = "get_drift"
    mock_tc.function.arguments = json.dumps({"model_id": "m1"})

    mock_client = MagicMock()
    mock_groq.return_value = mock_client
    mock_async_groq.return_value = MagicMock()
    mock_client.chat.completions.create.return_value = _groq_mock_response(
        content="", tool_calls=[mock_tc]
    )

    from finsight.llm.groq_provider import GroqProvider
    result = GroqProvider().complete(
        [{"role": "user", "content": "check drift"}],
        tools=[{"type": "function", "function": {"name": "get_drift", "parameters": {}}}],
    )

    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_drift"
    assert result.tool_calls[0].arguments == {"model_id": "m1"}


def test_groq_raises_without_api_key():
    with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
        from finsight.llm.groq_provider import GroqProvider
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            GroqProvider()


# ── GeminiProvider tests ──────────────────────────────────────────────────────

def _gemini_mock_response(content: str = "answer"):
    part = MagicMock()
    part.text = content
    part.function_call = None

    candidate = MagicMock()
    candidate.content.parts = [part]

    usage = MagicMock()
    usage.prompt_token_count = 5
    usage.candidates_token_count = 10
    usage.total_token_count = 15

    resp = MagicMock()
    resp.candidates = [candidate]
    resp.usage_metadata = usage
    return resp


@patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
@patch("finsight.llm.gemini_provider.genai.Client")
def test_gemini_complete_returns_llm_response(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = _gemini_mock_response("gemini reply")

    from finsight.llm.gemini_provider import GeminiProvider
    result = GeminiProvider(role="reasoning").complete([{"role": "user", "content": "hi"}])

    assert isinstance(result, LLMResponse)
    assert result.content == "gemini reply"
    assert result.usage.total_tokens == 15


def test_gemini_raises_without_api_key():
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
        from finsight.llm.gemini_provider import GeminiProvider
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            GeminiProvider()


# ── Provider swap via get_llm() ───────────────────────────────────────────────

@patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "test-key"})
@patch("finsight.llm.groq_provider.AsyncGroq")
@patch("finsight.llm.groq_provider.Groq")
def test_get_llm_returns_groq(mock_groq, mock_async_groq):
    mock_groq.return_value = MagicMock()
    mock_async_groq.return_value = MagicMock()

    from finsight.llm.config import get_llm
    from finsight.llm.groq_provider import GroqProvider
    assert isinstance(get_llm(), GroqProvider)


@patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"})
@patch("finsight.llm.gemini_provider.genai.Client")
def test_get_llm_returns_gemini(mock_client_cls):
    mock_client_cls.return_value = MagicMock()

    from finsight.llm.config import get_llm
    from finsight.llm.gemini_provider import GeminiProvider
    assert isinstance(get_llm(), GeminiProvider)


def test_get_llm_raises_on_unknown_provider():
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
        from finsight.llm.config import get_llm
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            get_llm()
