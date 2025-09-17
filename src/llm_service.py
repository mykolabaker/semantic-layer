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
        max_tokens = kwargs.get("max_tokens", 4000)
        temperature = kwargs.get("temperature", 0.1)

        self.logger.debug(f"OpenAI request - Model: {self.model}, Max tokens: {max_tokens}, Temperature: {temperature}")
        self.logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            import time
            start_time = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            request_time = time.time() - start_time
            content = response.choices[0].message.content or ""

            # Log response details
            self.logger.debug(f"OpenAI response received in {request_time:.2f} seconds")
            self.logger.debug(f"Response length: {len(content)} characters")

            if hasattr(response, 'usage'):
                usage = response.usage
                self.logger.info(f"Token usage - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")

            return content

        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, 'response'):
                self.logger.error(f"HTTP status: {getattr(e.response, 'status_code', 'Unknown')}")
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
        max_tokens = kwargs.get("max_tokens", 4000)
        temperature = kwargs.get("temperature", 0.1)

        self.logger.debug(f"Anthropic request - Model: {self.model}, Max tokens: {max_tokens}, Temperature: {temperature}")
        self.logger.debug(f"Prompt length: {len(prompt)} characters")

        try:
            import time
            start_time = time.time()

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            request_time = time.time() - start_time
            content = response.content[0].text

            # Log response details
            self.logger.debug(f"Anthropic response received in {request_time:.2f} seconds")
            self.logger.debug(f"Response length: {len(content)} characters")

            if hasattr(response, 'usage'):
                usage = response.usage
                self.logger.info(f"Token usage - Input: {usage.input_tokens}, Output: {usage.output_tokens}")

            return content

        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, 'response'):
                self.logger.error(f"HTTP status: {getattr(e.response, 'status_code', 'Unknown')}")
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
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Initializing LLM service with provider: {config.provider}")
        self.logger.debug(f"LLM model: {config.model}")
        self.logger.debug(f"Max tokens: {config.max_tokens}")
        self.logger.debug(f"Temperature: {config.temperature}")
        self.logger.debug(f"Retry attempts: {config.retry_attempts}")
        self.logger.debug(f"Cache enabled: {config.cache_enabled}")

        self.provider = self._create_provider()
        self.cache = ResponseCache() if config.cache_enabled else None

        if self.cache:
            self.logger.info(f"Response cache initialized at: {self.cache.cache_dir}")
        else:
            self.logger.info("Response cache disabled")

        self.logger.info("LLM service initialization completed")

    def _create_provider(self) -> LLMProvider:
        """Create appropriate LLM provider based on configuration."""
        self.logger.debug(f"Creating LLM provider for: {self.config.provider}")

        if self.config.provider == "openai":
            self.logger.info("Initializing OpenAI provider")
            return OpenAIProvider(self.config.api_key, self.config.model)
        elif self.config.provider == "anthropic":
            self.logger.info("Initializing Anthropic provider")
            return AnthropicProvider(self.config.api_key, self.config.model)
        else:
            self.logger.error(f"Unsupported LLM provider: {self.config.provider}")
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic."""
        self.logger.debug(f"Starting retry logic with {self.config.retry_attempts} max attempts")

        for attempt in range(self.config.retry_attempts):
            try:
                self.logger.debug(f"Executing attempt {attempt + 1}/{self.config.retry_attempts}")
                result = func(*args, **kwargs)

                if attempt > 0:
                    self.logger.info(f"Function succeeded on attempt {attempt + 1}")

                return result

            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    self.logger.error(f"All {self.config.retry_attempts} attempts failed. Final error: {e}")
                    self.logger.error(f"Error type: {type(e).__name__}")
                    raise e

                wait_time = 2**attempt
                self.logger.warning(
                    f"Attempt {attempt + 1}/{self.config.retry_attempts} failed: {e}"
                )
                self.logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    def _generate_with_cache(self, prompt: str) -> str:
        """Generate response with caching support."""
        prompt_length = len(prompt)
        self.logger.debug(f"Generating response for prompt of {prompt_length} characters")

        cache_key = None
        if self.cache:
            cache_key = self.cache.get_cache_key(prompt, self.config.model)
            self.logger.debug(f"Cache key: {cache_key[:16]}...")

            cached = self.cache.get_cached_response(cache_key)
            if cached:
                self.logger.info("Using cached LLM response")
                self.logger.debug(f"Cached response length: {len(cached)} characters")
                return cached
            else:
                self.logger.debug("No cached response found")

        self.logger.info(f"Sending request to LLM ({self.config.provider}/{self.config.model})")
        start_time = time.time()

        response = self._retry_with_backoff(
            self.provider.generate_response,
            prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

        request_time = time.time() - start_time
        response_length = len(response)

        self.logger.info(f"LLM response received in {request_time:.2f} seconds")
        self.logger.debug(f"Response length: {response_length} characters")
        self.logger.debug(f"Response preview: {response[:200]}...")

        if self.cache and cache_key:
            self.logger.debug("Caching LLM response")
            self.cache.cache_response(cache_key, response)

        return response

    def generate_entity_identification(
        self, schema_context: Dict[str, Any], business_context: str
    ) -> Dict[str, Any]:
        """First LLM call: Identify core business entities from database schema."""
        from src.config import Config

        self.logger.info("Starting entity identification generation")
        self.logger.debug(f"Schema context contains {len(schema_context.get('tables', {}))} tables")
        self.logger.debug(f"Business context length: {len(business_context)} characters")

        prompt_template = Config().get_prompt_templates()["entity_identification"]
        self.logger.debug("Building entity identification prompt")

        schema_json = json.dumps(schema_context, indent=2)
        self.logger.debug(f"Schema JSON length: {len(schema_json)} characters")

        prompt = prompt_template.format(
            schema_context=schema_json,
            business_context=business_context,
        )

        prompt_length = len(prompt)
        self.logger.info(f"Generated prompt with {prompt_length} characters")

        if prompt_length > 100000:
            self.logger.warning(f"Large prompt size: {prompt_length} characters - may hit token limits")

        self.logger.info("Sending entity identification request to LLM")
        response = self._generate_with_cache(prompt)

        self.logger.debug("Parsing LLM response as JSON")

        # Check if response contains ```json format
        if "```json" in response and "json" in response.lower():
            self.logger.debug("Response appears to contain JSON in markdown format")
            cleaned_response = self._extract_json_from_markdown(response)
            try:
                parsed_response = json.loads(cleaned_response)
                entity_count = len(parsed_response.get('entities', []))
                self.logger.info(f"Successfully parsed entity identification response with {entity_count} entities")
                return parsed_response
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON after markdown extraction: {e}")
                raise ValueError("Unable to parse LLM response as valid JSON")
        else:
            try:
                parsed_response = json.loads(response)
                entity_count = len(parsed_response.get('entities', []))
                self.logger.info(f"Successfully parsed entity identification response with {entity_count} entities")
                return parsed_response
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON response: {e}")
                raise ValueError("Unable to parse LLM response as valid JSON")

    def generate_entity_details(
        self,
        entity_name: str,
        entity_context: Dict[str, Any],
        schema_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Second LLM call: Generate detailed entity definition."""
        from src.config import Config

        self.logger.info(f"Starting entity details generation for: {entity_name}")

        # Extract relevant schema for this entity
        relevant_tables = entity_context.get("primary_tables", [])
        self.logger.debug(f"Entity {entity_name} uses tables: {relevant_tables}")

        relevant_schema = {}
        found_tables = []
        missing_tables = []

        for table_name in relevant_tables:
            if table_name in schema_context.get("tables", {}):
                relevant_schema[table_name] = schema_context["tables"][table_name]
                found_tables.append(table_name)
            else:
                missing_tables.append(table_name)

        if missing_tables:
            self.logger.warning(f"Missing tables for entity {entity_name}: {missing_tables}")

        self.logger.debug(f"Found schema for {len(found_tables)} tables: {found_tables}")

        prompt_template = Config().get_prompt_templates()["entity_details"]
        self.logger.debug("Building entity details prompt")

        relevant_schema_json = json.dumps(relevant_schema, indent=2)
        sample_data_dict = {k: v.get("sample_data", []) for k, v in relevant_schema.items()}
        sample_data_json = json.dumps(sample_data_dict, indent=2)

        self.logger.debug(f"Relevant schema JSON length: {len(relevant_schema_json)} characters")
        self.logger.debug(f"Sample data JSON length: {len(sample_data_json)} characters")

        prompt = prompt_template.format(
            entity_name=entity_name,
            entity_description=entity_context.get("description", ""),
            primary_tables=entity_context.get("primary_tables", []),
            business_function=entity_context.get("business_function", ""),
            relevant_schema=relevant_schema_json,
            sample_data=sample_data_json,
        )

        prompt_length = len(prompt)
        self.logger.info(f"Generated entity details prompt with {prompt_length} characters for {entity_name}")

        self.logger.info(f"Sending entity details request to LLM for: {entity_name}")
        response = self._generate_with_cache(prompt)

        self.logger.debug(f"Parsing entity details response for: {entity_name}")

        # Check if response contains ```json format
        if "```json" in response and "json" in response.lower():
            self.logger.debug("Response appears to contain JSON in markdown format")
            cleaned_response = self._extract_json_from_markdown(response)
            try:
                parsed_response = json.loads(cleaned_response)

                # Log details about the generated entity
                attrs_count = len(parsed_response.get('attributes', {}))
                relations_count = len(parsed_response.get('relations', {}))
                has_base_query = 'base_query' in parsed_response

                self.logger.info(f"Successfully generated entity {entity_name}: {attrs_count} attributes, {relations_count} relations, base_query={has_base_query}")

                return parsed_response
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON after markdown extraction for entity {entity_name}: {e}")
                raise ValueError("Unable to parse LLM response as valid JSON")
        else:
            try:
                parsed_response = json.loads(response)

                # Log details about the generated entity
                attrs_count = len(parsed_response.get('attributes', {}))
                relations_count = len(parsed_response.get('relations', {}))
                has_base_query = 'base_query' in parsed_response

                self.logger.info(f"Successfully generated entity {entity_name}: {attrs_count} attributes, {relations_count} relations, base_query={has_base_query}")

                return parsed_response
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON response for entity {entity_name}: {e}")
                raise ValueError("Unable to parse LLM response as valid JSON")



    def _extract_json_from_markdown(self, response: str) -> str:
        """Extract JSON content from markdown code blocks."""
        import re

        # Try to find JSON content within ```json ... ``` blocks
        json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        match = re.search(json_pattern, response, re.DOTALL | re.IGNORECASE)

        if match:
            self.logger.debug("Found JSON content within markdown code blocks")
            return match.group(1).strip()

        # If no markdown blocks found, return original response
        return response
