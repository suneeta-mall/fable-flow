"""
Robust continuation service using OpenAI's standard finish_reason detection.
This is the industry-standard approach used by production AI applications.
"""

import re
from typing import Any, Optional

from loguru import logger
from openai import AsyncClient

from .config import config


class ContinuationService:
    """
    Robust continuation service using hybrid detection approach.

    This service handles long-form content generation by:
    1. Using OpenAI's finish_reason to detect token-limit truncations
    2. Analyzing content for model-generated continuation messages
    3. Maintaining conversation context for natural continuation
    4. Cleaning continuation artifacts for seamless content flow
    """

    def __init__(self, client: AsyncClient, model_name: str):
        self.client = client
        self.model_name = model_name
        self.config = config.model.continuation

    async def generate_with_continuation(
        self, messages: list[dict[str, str]], max_tokens: int | None = None, **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """
        Generate content with automatic continuation using hybrid detection.

        Uses both OpenAI's finish_reason detection AND content-based analysis
        to handle cases where models add their own continuation messages.

        Returns:
            Tuple of (complete_content, metadata)

        Metadata includes:
            - total_continuations: number of continuation calls made
            - finish_reason: final finish reason
            - total_tokens: estimated total tokens used
            - completion_strategy: always "hybrid_detection"
        """
        if not self.config.enabled:
            return await self._single_generation(messages, max_tokens, **kwargs)

        # Always use hybrid approach: both finish_reason AND content-based detection
        return await self._generate_with_continuation_detection(messages, max_tokens, **kwargs)

    async def _generate_with_continuation_detection(
        self, messages: list[dict[str, str]], max_tokens: int | None = None, **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Robust continuation logic using both finish_reason AND content analysis."""

        full_content = ""
        continuation_count = 0
        total_tokens = 0
        finish_reason = ""
        current_messages = messages.copy()

        # Use configured chunk size or provided max_tokens
        chunk_tokens = max_tokens or self.config.chunk_size

        while continuation_count <= self.config.max_continuations:
            try:
                # Generate single chunk
                response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=current_messages,
                    max_tokens=chunk_tokens,
                    stream=config.model.stream,
                    **kwargs,
                )

                # Extract content and metadata
                if config.model.stream:
                    content, finish_reason, tokens = await self._handle_streaming_response(response)
                else:
                    choice = response.choices[0]
                    content = choice.message.content
                    finish_reason = choice.finish_reason
                    tokens = (
                        response.usage.total_tokens
                        if response.usage
                        else self._estimate_tokens(content)
                    )

                # Accumulate content
                if continuation_count == 0:
                    full_content = content
                else:
                    full_content = self._merge_continuation(full_content, content)

                total_tokens += tokens

                logger.info(
                    f"Generated chunk {continuation_count + 1}: "
                    f"{len(content)} chars, finish_reason: {finish_reason}"
                )

                # Check finish reason (OpenAI standard) AND content-based continuation indicators
                if finish_reason == "stop":
                    # Check for model-generated continuation indicators even with stop
                    if self._has_continuation_indicators(content):
                        logger.info(
                            "🔄 Model indicated continuation despite finish_reason=stop, continuing..."
                        )
                        continuation_count += 1

                        if continuation_count <= self.config.max_continuations:
                            # Clean the continuation indicator from content before adding to messages
                            cleaned_content = self._clean_continuation_indicators(content)
                            if continuation_count == 1:
                                full_content = cleaned_content
                            else:
                                full_content = self._merge_continuation(
                                    full_content, cleaned_content
                                )

                            current_messages = self._create_continuation_messages(
                                messages, full_content
                            )
                        else:
                            logger.warning(
                                f"⚠️ Maximum continuations reached ({self.config.max_continuations})"
                            )
                            break
                    else:
                        # Natural completion - we're done!
                        logger.info(f"✅ Natural completion after {continuation_count + 1} chunks")
                        break

                elif finish_reason == "length":
                    # Hit token limit - need continuation
                    continuation_count += 1

                    if continuation_count <= self.config.max_continuations:
                        logger.info(
                            f"🔄 Token limit reached, continuing ({continuation_count}/{self.config.max_continuations})"
                        )
                        current_messages = self._create_continuation_messages(
                            messages, full_content
                        )
                    else:
                        logger.warning(
                            f"⚠️ Maximum continuations reached ({self.config.max_continuations})"
                        )
                        break

                elif finish_reason in ["content_filter", "function_call"]:
                    # Content filtered or function call - stop
                    logger.info(f"⚠️ Generation stopped: {finish_reason}")
                    break

                else:
                    # Unknown finish reason - treat as potential continuation
                    logger.warning(f"Unknown finish_reason: {finish_reason}, stopping")
                    break

            except Exception as e:
                logger.error(f"Error during continuation {continuation_count}: {e}")
                break

        metadata = {
            "total_continuations": continuation_count,
            "finish_reason": finish_reason,
            "total_tokens": total_tokens,
            "completion_strategy": "hybrid_detection",
        }

        logger.info(
            f"🎉 Final result: {len(full_content)} chars, {continuation_count} continuations"
        )
        return full_content, metadata

    async def _handle_streaming_response(self, response) -> tuple[str, str, int]:
        """Handle streaming response and extract finish_reason."""
        content_parts = []
        finish_reason = None

        async for chunk in response:
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.delta.content:
                    content_parts.append(choice.delta.content)
                if choice.finish_reason:
                    finish_reason = choice.finish_reason

        content = "".join(content_parts)
        tokens = self._estimate_tokens(content)

        return content, finish_reason or "unknown", tokens

    def _create_continuation_messages(
        self, original_messages: list[dict[str, str]], partial_content: str
    ) -> list[dict[str, str]]:
        """Create conversation context for continuation."""

        # Create continuation using conversation pattern
        continuation_messages = original_messages.copy()

        # Add the assistant's partial response
        continuation_messages.append({"role": "assistant", "content": partial_content})

        # Add continuation request
        continuation_messages.append(
            {
                "role": "user",
                "content": "Please continue from exactly where you stopped. Do not repeat any content.",
            }
        )

        return continuation_messages

    def _merge_continuation(self, original: str, continuation: str) -> str:
        """Merge continuation content with original."""
        continuation = continuation.strip()

        # Remove common continuation artifacts
        continuation_prefixes = [
            "Continuing from where I left off:",
            "Continuing:",
            "Here's the continuation:",
            "Resuming:",
        ]

        for prefix in continuation_prefixes:
            if continuation.startswith(prefix):
                continuation = continuation[len(prefix) :].strip()
                break

        # Smart merge - avoid double spacing
        if original.endswith("\n"):
            return original + continuation
        else:
            return original + "\n\n" + continuation

    async def _single_generation(
        self, messages: list[dict[str, str]], max_tokens: int | None = None, **kwargs
    ) -> tuple[str, dict[str, Any]]:
        """Fallback to single generation when continuation is disabled."""

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=max_tokens or config.model.max_tokens,
            stream=config.model.stream,
            **kwargs,
        )

        if config.model.stream:
            content, finish_reason, tokens = await self._handle_streaming_response(response)
        else:
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason
            tokens = (
                response.usage.total_tokens if response.usage else self._estimate_tokens(content)
            )

        metadata = {
            "total_continuations": 0,
            "finish_reason": finish_reason,
            "total_tokens": tokens,
            "completion_strategy": "single_generation",
        }

        return content, metadata

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters for most models)."""
        return len(text) // 4

    def _has_continuation_indicators(self, content: str) -> bool:
        """
        Detect model-generated continuation indicators using robust pattern matching.

        This handles cases where models add their own continuation messages
        even when finish_reason is 'stop'.
        """
        if not content:
            return False

        # Convert to lowercase for case-insensitive matching
        content_lower = content.lower().strip()

        # Robust patterns for continuation indicators
        continuation_patterns = [
            # Bracket-style indicators
            "[continuing with remaining chapters in next response due to length...]",
            "[continuing in next response due to length constraints...]",
            "[continued in next response due to length limits...]",
            "[continuation follows in next response...]",
            "[remaining content in next response...]",
            # Parenthetical indicators
            "(continuing with remaining chapters in next response due to length...)",
            "(continued in next response due to length constraints...)",
            "(continuation follows due to length limits...)",
            # Direct statements
            "continuing with remaining chapters in next response due to length",
            "continued in next response due to length constraints",
            "continuation follows in next response",
            "remaining chapters will be provided in the next response",
            # General patterns
            "due to length constraints",
            "due to length limits",
            "in next response due to length",
            "continuing in next response",
            "continuation follows",
        ]

        # Check if content ends with any continuation pattern
        for pattern in continuation_patterns:
            if content_lower.endswith(pattern.lower()):
                logger.info(f"🔍 Detected continuation indicator: '{pattern}'")
                return True

        # Check last 200 characters for any pattern (handles partial matches)
        tail_content = content_lower[-200:] if len(content_lower) > 200 else content_lower
        for pattern in continuation_patterns:
            if pattern.lower() in tail_content:
                logger.info(f"🔍 Detected continuation indicator in tail: '{pattern}'")
                return True

        return False

    def _clean_continuation_indicators(self, content: str) -> str:
        """
        Remove continuation indicators from content while preserving structure.

        This ensures clean content without continuation artifacts.
        """
        if not content:
            return content

        # Patterns to remove (more comprehensive than detection for cleaning)
        patterns_to_remove = [
            r"\[continuing with remaining chapters in next response due to length\.\.\.?\]",
            r"\[continuing in next response due to length constraints\.\.\.?\]",
            r"\[continued in next response due to length limits\.\.\.?\]",
            r"\[continuation follows in next response\.\.\.?\]",
            r"\[remaining content in next response\.\.\.?\]",
            r"\(continuing with remaining chapters in next response due to length\.\.\.?\)",
            r"\(continued in next response due to length constraints\.\.\.?\)",
            r"\(continuation follows due to length limits\.\.\.?\)",
            # Direct statements at end of content
            r"continuing with remaining chapters in next response due to length\.?$",
            r"continued in next response due to length constraints\.?$",
            r"continuation follows in next response\.?$",
            r"remaining chapters will be provided in the next response\.?$",
        ]

        cleaned_content = content

        # Apply each pattern removal
        for pattern in patterns_to_remove:
            cleaned_content = re.sub(
                pattern, "", cleaned_content, flags=re.IGNORECASE | re.MULTILINE
            )

        # Clean up any trailing whitespace or newlines after removal
        cleaned_content = cleaned_content.rstrip("\n\r\t ")

        # If we removed content, log it
        if len(cleaned_content) < len(content):
            removed_chars = len(content) - len(cleaned_content)
            logger.info(f"🧹 Cleaned {removed_chars} characters of continuation indicators")

        return cleaned_content


class MessageConverter:
    """Convert between different message formats."""

    @staticmethod
    def to_dict_format(messages: list[Any]) -> list[dict[str, str]]:
        """Convert autogen message objects to dict format."""
        dict_messages = []

        for msg in messages:
            if hasattr(msg, "role") and hasattr(msg, "content"):
                # It's already a dict-like object
                dict_messages.append(
                    {"role": msg.role if hasattr(msg, "role") else "user", "content": msg.content}
                )
            elif hasattr(msg, "content"):
                # It's a Message object like SystemMessage, UserMessage
                role = "system" if "System" in type(msg).__name__ else "user"
                if "Assistant" in type(msg).__name__:
                    role = "assistant"

                dict_messages.append({"role": role, "content": msg.content})
            elif isinstance(msg, dict):
                # Already in dict format
                dict_messages.append(msg)
            else:
                # Fallback
                dict_messages.append({"role": "user", "content": str(msg)})

        return dict_messages
