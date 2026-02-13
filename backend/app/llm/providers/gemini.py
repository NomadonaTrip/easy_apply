"""Google Gemini LLM provider implementation using google-genai SDK."""

from typing import AsyncIterator

from google import genai
from google.genai import types

from ..base import LLMProvider, Tool
from ..types import GenerationConfig, Message, Role, ToolCall


class GeminiProvider(LLMProvider):
    """
    Gemini API implementation of LLMProvider using the new google-genai SDK.

    Supports:
    - Text generation (single and streaming)
    - Function calling (tool use)
    - System instructions (for skills)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
    ):
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key
            model: Model name (default: gemini-2.0-flash)
        """
        self._client = genai.Client(api_key=api_key)
        self._model_name = model
        self._system_instruction: str | None = None

    def set_system_instruction(self, instruction: str) -> None:
        """Set the system instruction (e.g., from SKILL.md)."""
        self._system_instruction = instruction

    def get_model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    def _build_contents(self, messages: list[Message]) -> list[types.Content]:
        """Convert abstract messages to Gemini content format."""
        contents = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                # System messages are handled via system_instruction
                continue

            if msg.role == Role.USER:
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=msg.content)],
                    )
                )

            elif msg.role == Role.ASSISTANT:
                parts = []
                if msg.content:
                    parts.append(types.Part.from_text(text=msg.content))

                # Add function calls if present
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        parts.append(
                            types.Part.from_function_call(
                                name=tc.name,
                                args=tc.arguments,
                            )
                        )

                contents.append(types.Content(role="model", parts=parts))

            elif msg.role == Role.TOOL:
                # Tool/function response
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=msg.tool_call_id or "unknown",
                                response={"result": msg.content},
                            )
                        ],
                    )
                )

        return contents

    def _build_tools(self, tools: list[Tool]) -> list[types.Tool]:
        """Convert abstract tools to Gemini tool format."""
        function_declarations = []

        for tool in tools:
            fd = types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters_schema,
            )
            function_declarations.append(fd)

        return [types.Tool(function_declarations=function_declarations)]

    def _build_config(
        self,
        config: GenerationConfig | None,
        tools: list[types.Tool] | None = None,
    ) -> types.GenerateContentConfig:
        """Build generation config."""
        if not config:
            config = GenerationConfig()

        gen_config = types.GenerateContentConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            top_p=config.top_p,
            top_k=config.top_k,
            stop_sequences=config.stop_sequences if config.stop_sequences else None,
            system_instruction=self._system_instruction,
            response_mime_type=config.response_mime_type,
        )

        if tools:
            gen_config.tools = tools
            # Disable automatic function calling - we want to handle it ourselves
            gen_config.automatic_function_calling = types.AutomaticFunctionCallingConfig(
                disable=True
            )

        return gen_config

    def _extract_tool_calls(self, response) -> list[ToolCall]:
        """Extract function calls from Gemini response."""
        tool_calls = []

        if not response.candidates:
            return tool_calls

        for candidate in response.candidates:
            if not candidate.content or not candidate.content.parts:
                continue

            for part in candidate.content.parts:
                if part.function_call:
                    fc = part.function_call
                    tool_calls.append(
                        ToolCall(
                            id=fc.name,  # Use function name as ID
                            name=fc.name,
                            arguments=dict(fc.args) if fc.args else {},
                        )
                    )

        return tool_calls

    def _extract_finish_reason(self, response) -> str | None:
        """Extract finish reason from Gemini response.

        Returns string like "STOP", "MAX_TOKENS", "SAFETY", etc.
        Returns None if no candidates present.
        """
        if response.candidates and len(response.candidates) > 0:
            reason = response.candidates[0].finish_reason
            # The Gemini SDK returns a FinishReason enum; convert to string
            return reason.name if reason else None
        return None

    def _extract_text(self, response) -> str:
        """Extract text content from Gemini response."""
        if hasattr(response, "text") and response.text:
            return response.text

        text_parts = []
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.text:
                            text_parts.append(part.text)

        return "".join(text_parts)

    async def generate(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> Message:
        """Generate a single response."""
        contents = self._build_contents(messages)
        gen_config = self._build_config(config)

        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=gen_config,
        )

        return Message(
            role=Role.ASSISTANT,
            content=self._extract_text(response),
            finish_reason=self._extract_finish_reason(response),
        )

    async def generate_stream(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """Generate a streaming response."""
        contents = self._build_contents(messages)
        gen_config = self._build_config(config)

        async for chunk in self._client.aio.models.generate_content_stream(
            model=self._model_name,
            contents=contents,
            config=gen_config,
        ):
            text = self._extract_text(chunk)
            if text:
                yield text

    async def generate_with_tools(
        self,
        messages: list[Message],
        tools: list[Tool],
        config: GenerationConfig | None = None,
    ) -> tuple[Message, list[ToolCall]]:
        """Generate a response with tool/function calling support."""
        contents = self._build_contents(messages)
        gemini_tools = self._build_tools(tools)
        gen_config = self._build_config(config, tools=gemini_tools)

        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=gen_config,
        )

        tool_calls = self._extract_tool_calls(response)
        content = self._extract_text(response)

        return (
            Message(
                role=Role.ASSISTANT,
                content=content,
                tool_calls=tool_calls,
                finish_reason=self._extract_finish_reason(response),
            ),
            tool_calls,
        )
