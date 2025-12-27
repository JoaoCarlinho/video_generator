"""LLM Client abstraction supporting multiple providers (OpenAI, AWS Bedrock).

This module provides a unified async interface for LLM chat completions
that works with both OpenAI and AWS Bedrock Claude models.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Chat message with role and content."""
    role: str
    content: str


@dataclass
class Choice:
    """Response choice containing a message."""
    message: Message
    index: int = 0
    finish_reason: str = "stop"


@dataclass
class ChatCompletionResponse:
    """Chat completion response matching OpenAI format."""
    choices: List[Choice]
    model: str
    usage: Optional[Dict[str, int]] = None


class ChatCompletions:
    """Chat completions interface."""

    def __init__(self, client: 'BaseLLMClient'):
        self._client = client

    async def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_completion_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatCompletionResponse:
        """Create a chat completion."""
        # Support both max_completion_tokens and max_tokens
        max_tok = max_completion_tokens or max_tokens or 4096
        return await self._client._create_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tok,
            **kwargs
        )


class Chat:
    """Chat interface containing completions."""

    def __init__(self, client: 'BaseLLMClient'):
        self.completions = ChatCompletions(client)


class BaseLLMClient:
    """Base class for LLM clients."""

    def __init__(self):
        self.chat = Chat(self)

    async def _create_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> ChatCompletionResponse:
        raise NotImplementedError


class BedrockLLMClient(BaseLLMClient):
    """AWS Bedrock LLM client with OpenAI-compatible interface.

    Uses Claude models via AWS Bedrock for chat completions.
    """

    def __init__(self, region_name: str = "us-east-1"):
        """Initialize Bedrock client.

        Args:
            region_name: AWS region for Bedrock service
        """
        super().__init__()
        import boto3
        from botocore.config import Config

        # Configure timeouts to prevent hanging
        # connect_timeout: time to establish connection (10s)
        # read_timeout: time to wait for response (120s - LLM can be slow)
        bedrock_config = Config(
            connect_timeout=10,
            read_timeout=120,
            retries={'max_attempts': 2, 'mode': 'standard'}
        )

        self._bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name=region_name,
            config=bedrock_config
        )
        self._region = region_name
        # Default model mapping
        self._model_map = {
            "gpt-4o-mini": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
            "gpt-4o": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "gpt-4": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "gpt-5.1": "us.anthropic.claude-sonnet-4-20250514-v1:0",  # Map to Claude Sonnet 4
        }
        logger.info(f"BedrockLLMClient initialized (region: {region_name})")

    def _map_model(self, model: str) -> str:
        """Map OpenAI model name to Bedrock model ID."""
        return self._model_map.get(model, "us.anthropic.claude-sonnet-4-20250514-v1:0")

    async def _create_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> ChatCompletionResponse:
        """Create a chat completion using Bedrock Claude.

        Args:
            model: Model name (will be mapped to Bedrock model ID)
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response

        Returns:
            ChatCompletionResponse with generated content
        """
        bedrock_model = self._map_model(model)

        # Convert messages to Claude format
        system_prompt = None
        claude_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                system_prompt = content
            else:
                # Claude uses "user" and "assistant" roles
                claude_role = "assistant" if role == "assistant" else "user"
                claude_messages.append({
                    "role": claude_role,
                    "content": content
                })

        # Ensure messages alternate between user and assistant
        # If we have consecutive messages with same role, merge them
        merged_messages = []
        for msg in claude_messages:
            if merged_messages and merged_messages[-1]["role"] == msg["role"]:
                merged_messages[-1]["content"] += "\n\n" + msg["content"]
            else:
                merged_messages.append(msg)

        # Build request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": merged_messages
        }

        if system_prompt:
            request_body["system"] = system_prompt

        try:
            # Run synchronous boto3 call in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._bedrock.invoke_model(
                    modelId=bedrock_model,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json"
                )
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            # Extract content from Claude response
            content = ""
            if "content" in response_body and response_body["content"]:
                content = response_body["content"][0].get("text", "")

            # Build OpenAI-compatible response
            return ChatCompletionResponse(
                choices=[
                    Choice(
                        message=Message(role="assistant", content=content),
                        index=0,
                        finish_reason=response_body.get("stop_reason", "stop")
                    )
                ],
                model=bedrock_model,
                usage={
                    "prompt_tokens": response_body.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": response_body.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": (
                        response_body.get("usage", {}).get("input_tokens", 0) +
                        response_body.get("usage", {}).get("output_tokens", 0)
                    )
                }
            )

        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            raise


class OpenAILLMClient(BaseLLMClient):
    """OpenAI LLM client wrapper for consistent interface."""

    def __init__(self, api_key: str):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
        """
        super().__init__()
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAILLMClient initialized")

    async def _create_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> ChatCompletionResponse:
        """Create a chat completion using OpenAI.

        Args:
            model: OpenAI model name
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            ChatCompletionResponse with generated content
        """
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_tokens,
            **kwargs
        )

        # Convert to our response format
        return ChatCompletionResponse(
            choices=[
                Choice(
                    message=Message(
                        role=response.choices[0].message.role,
                        content=response.choices[0].message.content or ""
                    ),
                    index=response.choices[0].index,
                    finish_reason=response.choices[0].finish_reason or "stop"
                )
            ],
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            } if response.usage else None
        )


def get_llm_client(
    provider: str = "bedrock",
    api_key: Optional[str] = None,
    region: str = "us-east-1"
) -> BaseLLMClient:
    """Factory function to get the appropriate LLM client.

    Args:
        provider: LLM provider ("bedrock" or "openai")
        api_key: API key (required for OpenAI)
        region: AWS region (for Bedrock)

    Returns:
        LLM client instance
    """
    if provider.lower() == "openai":
        if not api_key:
            raise ValueError("OpenAI API key is required")
        return OpenAILLMClient(api_key=api_key)
    elif provider.lower() == "bedrock":
        return BedrockLLMClient(region_name=region)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
