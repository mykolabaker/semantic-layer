"""
LLM service wrapper for handling API communications, caching,
and prompt management with OpenAI/Anthropic APIs.
"""

from typing import Dict, Any, Optional
import json
import hashlib
import time
import logging
from pathlib import Path
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
        try:
            import openai

            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
            self.logger = logging.getLogger(__name__)
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 4000),
                temperature=kwargs.get("temperature", 0.1),
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicProvider(LLMProvider):
    """Anthropic API provider implementation."""

    def __init__(self, api_key: str, model: str):
        """Initialize Anthropic provider."""
        try:
            import anthropic  # type: ignore

            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model
            self.logger = logging.getLogger(__name__)
        except ImportError:
            raise ImportError(
                "Anthropic library not installed. Run: pip install anthropic"
            )

    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Anthropic API."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 4000),
                temperature=kwargs.get("temperature", 0.1),
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise


class ResponseCache:
    """Simple file-based cache for LLM responses."""

    def __init__(self, cache_dir: str = ".cache"):
        """Initialize response cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model."""
        content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get_cached_response(self, cache_key: str) -> Optional[str]:
        """Retrieve cached response if available."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                data = json.load(f)
                return data.get("response")
        return None

    def cache_response(self, cache_key: str, response: str) -> None:
        """Store response in cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        with open(cache_file, "w") as f:
            json.dump({"response": response, "timestamp": time.time()}, f)


class LLMService:
    """Main service for LLM interactions with caching and error handling."""

    def __init__(self, config):
        """Initialize LLM service with configuration."""
        self.config = config
        self.provider = self._create_provider()
        self.cache = ResponseCache() if config.cache_enabled else None
        self.logger = logging.getLogger(__name__)

    def _create_provider(self) -> LLMProvider:
        """Create appropriate LLM provider based on configuration."""
        if self.config.provider == "openai":
            return OpenAIProvider(self.config.api_key, self.config.model)
        elif self.config.provider == "anthropic":
            return AnthropicProvider(self.config.api_key, self.config.model)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic."""
        for attempt in range(self.config.retry_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    raise e
                wait_time = 2**attempt
                self.logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                )
                time.sleep(wait_time)

    def _generate_with_cache(self, prompt: str) -> str:
        """Generate response with caching support."""
        if self.cache:
            cache_key = self.cache.get_cache_key(prompt, self.config.model)
            cached = self.cache.get_cached_response(cache_key)
            if cached:
                self.logger.info("Using cached LLM response")
                return cached

        response = self._retry_with_backoff(
            self.provider.generate_response,
            prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        if self.cache:
            self.cache.cache_response(cache_key, response)

        return response

    def generate_entity_identification(
        self, schema_context: Dict[str, Any], business_context: str
    ) -> Dict[str, Any]:
        """First LLM call: Identify core business entities from database schema."""
        from src.config import Config

        prompt_template = Config().get_prompt_templates()["entity_identification"]
        prompt = prompt_template.format(
            schema_context=json.dumps(schema_context, indent=2),
            business_context=business_context,
        )

        self.logger.info("Generating entity identification")
        response = self._generate_with_cache(prompt)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.warning("Invalid JSON response, attempting repair")
            return self.repair_json_response(response)

    def generate_entity_details(
        self,
        entity_name: str,
        entity_context: Dict[str, Any],
        schema_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Second LLM call: Generate detailed entity definition."""
        from src.config import Config

        # Extract relevant schema for this entity
        relevant_tables = entity_context.get("primary_tables", [])
        relevant_schema = {}
        for table_name in relevant_tables:
            if table_name in schema_context.get("tables", {}):
                relevant_schema[table_name] = schema_context["tables"][table_name]

        prompt_template = Config().get_prompt_templates()["entity_details"]
        prompt = prompt_template.format(
            entity_name=entity_name,
            entity_description=entity_context.get("description", ""),
            primary_tables=entity_context.get("primary_tables", []),
            business_function=entity_context.get("business_function", ""),
            relevant_schema=json.dumps(relevant_schema, indent=2),
            sample_data=json.dumps(
                {k: v.get("sample_data", []) for k, v in relevant_schema.items()},
                indent=2,
            ),
        )

        self.logger.info(f"Generating entity details for: {entity_name}")
        response = self._generate_with_cache(prompt)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.warning(
                f"Invalid JSON response for {entity_name}, attempting repair"
            )
            return self.repair_json_response(response)

    def repair_json_response(self, malformed_json: str) -> Dict[str, Any]:
        """Send malformed JSON back to LLM for automatic repair."""
        from src.config import Config

        prompt_template = Config().get_prompt_templates()["json_repair"]
        prompt = prompt_template.format(malformed_json=malformed_json)

        self.logger.info("Attempting JSON repair")
        response = self._generate_with_cache(prompt)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to repair JSON: {e}")
            raise ValueError("Unable to parse LLM response as valid JSON")

    def validate_json_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate JSON response from LLM."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self.repair_json_response(response)
