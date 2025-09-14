"""
Central configuration management for prompts, settings, and API parameters.
Manages LLM model identifiers, prompts, and application settings.
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Configuration for database connection."""
    connection_string: str
    timeout: int = 30


@dataclass
class LLMConfig:
    """Configuration for LLM API settings."""
    provider: str  # 'openai' or 'anthropic'
    model: str
    api_key: str
    max_tokens: int = 4000
    temperature: float = 0.1
    retry_attempts: int = 3
    cache_enabled: bool = True


class Config:
    """Main configuration class containing all settings."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # Load environment variables and set defaults
        pass

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        pass

    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        pass

    def get_prompt_templates(self) -> Dict[str, str]:
        """Get all prompt templates for LLM interactions."""
        pass

    def get_validation_settings(self) -> Dict[str, Any]:
        """Get validation configuration settings."""
        pass