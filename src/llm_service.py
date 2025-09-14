"""
LLM service wrapper for handling API communications, caching,
and prompt management with OpenAI/Anthropic APIs.
"""

from typing import Dict, Any, List, Optional
import json
import hashlib
import time
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM provider."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""

    def __init__(self, api_key: str, model: str):
        """Initialize OpenAI provider."""
        pass

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic API provider implementation."""

    def __init__(self, api_key: str, model: str):
        """Initialize Anthropic provider."""
        pass

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Anthropic API."""
        pass


class ResponseCache:
    """Simple file-based cache for LLM responses."""

    def __init__(self, cache_dir: str = ".cache"):
        """Initialize response cache."""
        pass

    def get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model."""
        pass

    def get_cached_response(self, cache_key: str) -> Optional[str]:
        """Retrieve cached response if available."""
        pass

    def cache_response(self, cache_key: str, response: str) -> None:
        """Store response in cache."""
        pass


class LLMService:
    """Main service for LLM interactions with caching and error handling."""

    def __init__(self, config: 'LLMConfig'):
        """Initialize LLM service with configuration."""
        pass

    def _create_provider(self) -> LLMProvider:
        """Create appropriate LLM provider based on configuration."""
        pass

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic."""
        pass

    def generate_entity_identification(self, schema_context: Dict[str, Any],
                                     business_context: str) -> Dict[str, Any]:
        """
        First LLM call: Identify core business entities from database schema.
        Returns structured response with entity names, tables, and descriptions.
        """
        pass

    def generate_entity_details(self, entity_name: str, entity_context: Dict[str, Any],
                               schema_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Second LLM call: Generate detailed entity definition including
        base_query, attributes, and relations.
        """
        pass

    def repair_json_response(self, malformed_json: str) -> str:
        """
        Send malformed JSON back to LLM for automatic repair.
        """
        pass

    def validate_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and validate JSON response from LLM.
        """
        pass