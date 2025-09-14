"""
Central configuration management for prompts, settings, and API parameters.
Manages LLM model identifiers, prompts, and application settings.
"""

import os
from typing import Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


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
        self.database_config = self.get_database_config()
        self.llm_config = self.get_llm_config()
        self.business_metrics = self._load_business_metrics()

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return DatabaseConfig(
            connection_string=os.getenv("DATABASE_CONNECTION_STRING", ""),
            timeout=int(os.getenv("DATABASE_TIMEOUT", "30")),
        )

    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        provider = os.getenv("LLM_PROVIDER", "openai")
        model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY", "")

        return LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
        )

    def get_prompt_templates(self) -> Dict[str, str]:
        """Get all prompt templates for LLM interactions."""
        return {
            "entity_identification": """You are an expert data analyst tasked with analyzing the Northwind database schema to identify core business entities.

CONTEXT:
Northwind Traders is a specialty foods wholesale distributor with the following business functions:
- Product Sourcing & Supply Chain (29 suppliers, 77 products in 8 categories)
- Sales & Customer Management (91 customers, 9 sales representatives, ~830 orders annually)
- Logistics & Distribution (3 shipping companies, international operations)

DATABASE SCHEMA:
{schema_context}

BUSINESS DOCUMENTATION:
{business_context}

TASK:
Analyze the database schema and identify 5-7 core business entities that represent meaningful business concepts. Think step-by-step:

1. First, understand the primary business processes
2. Identify which tables work together to represent complete business concepts
3. Group related tables into logical business entities
4. Ensure entities represent end-user business value, not just database tables

Return your analysis as JSON in this exact format:
{{
    "entities": [
        {{
            "name": "entity_key_name",
            "display_name": "Human Readable Name",
            "description": "What this entity represents in business terms",
            "primary_tables": ["table1", "table2"],
            "business_function": "Which core business function this supports",
            "rationale": "Why these tables form a coherent business entity"
        }}
    ]
}}

Focus on business value and user needs, not technical database structure.""",
            "entity_details": """You are an expert SQL developer creating a semantic layer entity definition.

ENTITY CONTEXT:
Entity Name: {entity_name}
Description: {entity_description}
Primary Tables: {primary_tables}
Business Function: {business_function}

RELEVANT SCHEMA:
{relevant_schema}

SAMPLE DATA:
{sample_data}

TASK:
Create a complete entity definition with optimized SQL. Follow these steps:

1. Design a base_query that joins the relevant tables efficiently
2. Create business-meaningful attributes with clear names
3. Include calculated fields that provide business value
4. Define relationships to other entities
5. Ensure all SQL is syntactically correct and optimized

EXAMPLE STRUCTURE:
{{
    "description": "Customer order transactions including details and totals",
    "base_query": "SELECT o.OrderID, o.CustomerID, o.OrderDate, c.CompanyName FROM Orders o JOIN Customers c ON o.CustomerID = c.CustomerID",
    "attributes": {{
        "order_id": {{
            "name": "Order ID",
            "description": "Unique identifier for each order",
            "sql": "o.OrderID"
        }},
        "total_amount": {{
            "name": "Total Order Amount",
            "description": "Total order value after discounts",
            "sql": "COALESCE(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 0)"
        }}
    }},
    "relations": {{
        "customer": {{
            "name": "Customer",
            "description": "Customer who placed the order",
            "target_entity": "customers",
            "sql": "o.CustomerID = c.CustomerID"
        }}
    }}
}}

REQUIREMENTS:
- Use efficient JOINs and avoid Cartesian products
- Create user-friendly attribute names
- Include relevant business metrics
- Ensure SQL is syntactically correct
- Return only valid JSON""",
            "json_repair": """The following JSON response has syntax errors. Please fix the JSON syntax while preserving all the content:

MALFORMED JSON:
{malformed_json}

Return only the corrected JSON with proper syntax.""",
        }

    def get_validation_settings(self) -> Dict[str, Any]:
        """Get validation configuration settings."""
        return {
            "enabled": os.getenv("VALIDATION_ENABLED", "true").lower() == "true",
            "sample_limit": 5,
            "sql_timeout": 10,
            "metric_tolerance": 0.1,  # 10% tolerance for business metrics
        }

    def _load_business_metrics(self) -> Dict[str, Any]:
        """Load known business metrics for validation."""
        return {
            "average_order_value": 1274,
            "average_items_per_order": 2.6,
            "total_orders": 830,
            "total_customers": 91,
            "total_products": 77,
            "total_employees": 9,
            "customer_retention_rate": 0.89,
            "average_fulfillment_days": 8,
        }
