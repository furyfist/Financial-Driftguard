"""Gemini implementation of BaseLLMProvider using the google-genai SDK."""

import os
from collections.abc import AsyncIterator

from google import genai
from google.genai import types

from .provider import BaseLLMProvider, LLMResponse, TokenUsage, ToolCall

_REASONING_MODEL = "gemini-2.5-pro"
_FAST_MODEL = "gemini-2.0-flash"


def _openai_tools_to_gemini(tools: list[dict]) -> list[types.Tool]:
    """Convert OpenAI-format tool definitions to Gemini FunctionDeclaration format."""
    declarations = []
    for tool in tools:
        if tool.get("type") != "function":
            continue
        fn = tool["function"]
        declarations.append(
            types.FunctionDeclaration(
                name=fn["name"],
                description=fn.get("description", ""),
                parameters=_schema_to_gemini(fn.get("parameters", {})),
            )
        )
    return [types.Tool(function_declarations=declarations)] if declarations else []


def _schema_to_gemini(schema: dict) -> types.Schema | None:
    """Recursively convert a JSON Schema dict to a Gemini Schema object."""
    if not schema:
        return None
    type_map = {
        "string": types.Type.STRING,
        "number": types.Type.NUMBER,
        "integer": types.Type.INTEGER,
        "boolean": types.Type.BOOLEAN,
        "array": types.Type.ARRAY,
        "object": types.Type.OBJECT,
    }
    gemini_type = type_map.get(schema.get("type", "string"), types.Type.STRING)
    properties = {
        name: _schema_to_gemini(prop)
        for name, prop in schema.get("properties", {}).items()
    }
    return types.Schema(
        type=gemini_type,
        description=schema.get("description"),
        properties=properties or None,
        required=schema.get("required"),
    )


def _openai_messages_to_gemini(
    messages: list[dict],
) -> tuple[str | None, list[types.Content]]:
    """Split OpenAI messages into a system instruction and Gemini Content list."""
    import json as _json
    system_instruction = None
    contents: list[types.Content] = []
    for msg in messages:
        role = msg["role"]
        text = msg.get("content") or ""
        if role == "system":
            system_instruction = text
        elif role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=text)]))
        elif role == "assistant":
            parts = []
            if text:
                parts.append(types.Part(text=text))
            for tc in msg.get("tool_calls") or []:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                args_dict = _json.loads(args) if isinstance(args, str) else args
                parts.append(types.Part(function_call=types.FunctionCall(
                    name=fn.get("name", ""),
                    args=args_dict,
                )))
            if parts:
                contents.append(types.Content(role="model", parts=parts))
        elif role == "tool":
            raw = msg.get("content", "{}")
            result_dict = _json.loads(raw) if isinstance(raw, str) else raw
            tool_name = msg.get("name", "tool_result")
            contents.append(types.Content(
                role="user",
                parts=[types.Part(function_response=types.FunctionResponse(
                    name=tool_name,
                    response=result_dict,
                ))],
            ))
    return system_instruction, contents


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using the google-genai SDK."""

    def __init__(self, role: str = "reasoning") -> None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GENAI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_GENAI_API_KEY must be set")
        model_env = "LLM_REASONING_MODEL" if role == "reasoning" else "LLM_FAST_MODEL"
        default = _REASONING_MODEL if role == "reasoning" else _FAST_MODEL
        self._model = os.getenv(model_env, default)
        self._client = genai.Client(api_key=api_key)

    def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        system_instruction, contents = _openai_messages_to_gemini(messages)
        gemini_tools = _openai_tools_to_gemini(tools) if tools else None

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            tools=gemini_tools,
        )

        def _call():
            return self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )

        resp = self._retry(_call)
        candidate = resp.candidates[0]

        content_text = ""
        tool_calls: list[ToolCall] | None = None

        for part in candidate.content.parts:
            if part.text:
                content_text += part.text
            elif part.function_call:
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append(
                    ToolCall(
                        name=part.function_call.name,
                        arguments=dict(part.function_call.args),
                    )
                )

        usage = resp.usage_metadata
        return LLMResponse(
            content=content_text,
            model=self._model,
            usage=TokenUsage(
                prompt_tokens=usage.prompt_token_count or 0,
                completion_tokens=usage.candidates_token_count or 0,
                total_tokens=usage.total_token_count or 0,
            ),
            tool_calls=tool_calls,
        )

    async def stream(self, messages: list[dict]) -> AsyncIterator[str]:
        # generate_content_stream is sync; wrapping in async generator is acceptable for dev use
        system_instruction, contents = _openai_messages_to_gemini(messages)
        config = types.GenerateContentConfig(system_instruction=system_instruction)
        for chunk in self._client.models.generate_content_stream(
            model=self._model,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                yield chunk.text
