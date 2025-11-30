"""
Centralized OpenAI client wrapper with proper timeout and retry configuration.
"""

from typing import Any, Optional

import httpx
from autogen_ext.models.openai import OpenAIChatCompletionClient

from .config import config


class FableFlowChatClient:
    """
    Centralized wrapper for OpenAI chat completion clients with proper timeout configuration.
    Eliminates code duplication and provides consistent configuration across the application.
    """

    @classmethod
    def create_http_client(cls) -> httpx.AsyncClient:
        """Create a new HTTP client with proper timeout configuration."""
        return httpx.AsyncClient(
            timeout=config.model.server.timeout,  # Simple timeout in seconds
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
        )

    @classmethod
    def create_chat_client(
        cls,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.9,
        seed: int = 42,
        additional_create_args: dict[str, Any] | None = None,
        reuse_http_client: bool = True,
    ) -> OpenAIChatCompletionClient:
        """
        Create a properly configured OpenAI chat completion client.

        Args:
            model: Model name (defaults to config.model.default)
            base_url: API base URL (defaults to config.model.server.url)
            api_key: API key (defaults to config.model.server.api_key)
            temperature: Sampling temperature
            seed: Random seed for reproducibility
            additional_create_args: Additional arguments for create() calls
            reuse_http_client: Whether to reuse HTTP client for performance (default: True)

        Returns:
            Configured OpenAIChatCompletionClient instance
        """
        # Use defaults from config if not provided
        model = model or config.model.default
        base_url = base_url or config.model.server.url
        api_key = api_key or config.model.server.api_key

        # Build create_args
        create_args = {
            "temperature": temperature,
            "seed": seed,
            "stream": config.model.stream,
        }

        # Add any additional create args
        if additional_create_args:
            create_args.update(additional_create_args)

        # Create client with or without HTTP client reuse
        client_kwargs: dict[str, Any] = {
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "create_args": create_args,
            "model_capabilities": {
                "chat": True,
                "completion": True,
                "function_calling": True,
                "max_tokens": config.model.max_tokens,
                "context_length": config.model.max_tokens * 2,
                "vision": True,
                "image_generation": True,
                "image_understanding": True,
                "json_output": True,
            },
        }

        # Use config setting if not explicitly specified
        if reuse_http_client is True:
            reuse_http_client = config.model.server.reuse_http_client

        if reuse_http_client:
            # Use shared HTTP client for better performance
            client_kwargs["http_client"] = cls._get_shared_http_client()
        else:
            # Create new HTTP client each time (simpler but less efficient)
            client_kwargs["http_client"] = cls.create_http_client()

        return OpenAIChatCompletionClient(**client_kwargs)

    # Shared client for reuse (only created when needed)
    _shared_http_client: httpx.AsyncClient | None = None

    @classmethod
    def _get_shared_http_client(cls) -> httpx.AsyncClient:
        """Get or create shared HTTP client for connection reuse."""
        if cls._shared_http_client is None:
            cls._shared_http_client = cls.create_http_client()
        return cls._shared_http_client

    @classmethod
    async def cleanup(cls) -> None:
        """Clean up shared HTTP client resources."""
        if cls._shared_http_client is not None:
            await cls._shared_http_client.aclose()
            cls._shared_http_client = None
