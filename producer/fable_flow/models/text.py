from __future__ import annotations

import openai
from loguru import logger

from fable_flow.config import config
from fable_flow.continuation import ContinuationService

_shared_client: openai.AsyncClient | None = None


def _get_client() -> openai.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = openai.AsyncClient(
            api_key=config.model.server.api_key,
            base_url=config.model.server.url,
            timeout=config.model.server.timeout,
            max_retries=config.model.server.max_retries,
        )
    return _shared_client


class EnhancedTextModel:
    """Async LLM client with automatic continuation for long outputs."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or config.model.default
        self.client = _get_client()
        self.continuation_service = ContinuationService(self.client, self.model_name)

    async def generate(
        self,
        prompt: str,
        system_message: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]
        kwargs: dict = {}
        kwargs["temperature"] = config.model.temperature if temperature is None else temperature

        content, metadata = await self.continuation_service.generate_with_continuation(
            messages, max_tokens=max_tokens, **kwargs
        )
        logger.info(f"Generation complete: {metadata}")
        return content
