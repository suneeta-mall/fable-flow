"""Continuation service for long-form LLM generation.

Detects token-limit truncation via finish_reason AND model-generated continuation
markers in content, requesting continuation up to a configured limit.
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger
from openai import AsyncClient

from .config import config

_CONTINUATION_MARKERS = [
    "[continuing with remaining chapters in next response due to length...]",
    "[continuing in next response due to length constraints...]",
    "[continued in next response due to length limits...]",
    "[continuation follows in next response...]",
    "[remaining content in next response...]",
    "(continuing with remaining chapters in next response due to length...)",
    "(continued in next response due to length constraints...)",
    "(continuation follows due to length limits...)",
    "continuing with remaining chapters in next response due to length",
    "continued in next response due to length constraints",
    "continuation follows in next response",
    "remaining chapters will be provided in the next response",
    "due to length constraints",
    "due to length limits",
    "in next response due to length",
    "continuing in next response",
    "continuation follows",
]

_MARKER_REGEXES = [re.compile(re.escape(m), re.IGNORECASE) for m in _CONTINUATION_MARKERS]

_PREFIX_ARTIFACTS = (
    "Continuing from where I left off:",
    "Continuing:",
    "Here's the continuation:",
    "Resuming:",
)


def _has_continuation_marker(content: str) -> bool:
    if not content:
        return False
    tail = content[-300:].lower()
    return any(m.lower() in tail for m in _CONTINUATION_MARKERS)


def _strip_continuation_markers(content: str) -> str:
    cleaned = content
    for regex in _MARKER_REGEXES:
        cleaned = regex.sub("", cleaned)
    return cleaned.rstrip("\n\r\t ")


def _strip_continuation_prefix(content: str) -> str:
    content = content.strip()
    for prefix in _PREFIX_ARTIFACTS:
        if content.startswith(prefix):
            return content[len(prefix) :].strip()
    return content


def _merge(original: str, addition: str) -> str:
    addition = _strip_continuation_prefix(addition)
    if original.endswith("\n"):
        return original + addition
    return original + "\n\n" + addition


class ContinuationService:
    """Generate long content by chaining model calls until natural completion."""

    def __init__(self, client: AsyncClient, model_name: str) -> None:
        self.client = client
        self.model_name = model_name
        self.config = config.model.continuation

    async def generate_with_continuation(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]]:
        if not self.config.enabled:
            return await self._single_generation(messages, max_tokens, **kwargs)

        chunk_tokens = max_tokens or self.config.chunk_size

        full_content = ""
        total_tokens = 0
        finish_reason = ""
        current_messages = list(messages)

        for attempt in range(self.config.max_continuations + 1):
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=current_messages,
                max_tokens=chunk_tokens,
                stream=config.model.stream,
                **kwargs,
            )

            if config.model.stream:
                content, finish_reason, tokens = await self._handle_streaming(response)
            else:
                choice = response.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason
                tokens = response.usage.total_tokens if response.usage else len(content) // 4

            has_marker = _has_continuation_marker(content)
            cleaned = _strip_continuation_markers(content) if has_marker else content

            full_content = cleaned if attempt == 0 else _merge(full_content, cleaned)
            total_tokens += tokens

            logger.info(
                f"Chunk {attempt + 1}: {len(cleaned)} chars, finish={finish_reason}"
                f"{', marker stripped' if has_marker else ''}"
            )

            needs_more = finish_reason == "length" or (finish_reason == "stop" and has_marker)

            if not needs_more:
                if finish_reason in ("content_filter", "function_call"):
                    logger.info(f"Generation stopped early: {finish_reason}")
                break

            if attempt >= self.config.max_continuations:
                logger.warning(
                    f"Hit max_continuations ({self.config.max_continuations}); returning partial"
                )
                break

            current_messages = list(messages) + [
                {"role": "assistant", "content": full_content},
                {
                    "role": "user",
                    "content": "Please continue from exactly where you stopped. Do not repeat content.",
                },
            ]

        metadata = {
            "total_continuations": attempt,
            "finish_reason": finish_reason,
            "total_tokens": total_tokens,
        }
        logger.info(f"Final: {len(full_content)} chars across {attempt + 1} chunk(s)")
        return full_content, metadata

    async def _handle_streaming(self, response) -> tuple[str, str, int]:
        parts: list[str] = []
        finish_reason: str | None = None
        async for chunk in response:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.delta.content:
                parts.append(choice.delta.content)
            if choice.finish_reason:
                finish_reason = choice.finish_reason
        content = "".join(parts)
        return content, finish_reason or "unknown", len(content) // 4

    async def _single_generation(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]]:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens or config.model.max_tokens,
            stream=config.model.stream,
            **kwargs,
        )
        if config.model.stream:
            content, finish_reason, tokens = await self._handle_streaming(response)
        else:
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason
            tokens = response.usage.total_tokens if response.usage else len(content) // 4
        return content, {
            "total_continuations": 0,
            "finish_reason": finish_reason,
            "total_tokens": tokens,
        }
