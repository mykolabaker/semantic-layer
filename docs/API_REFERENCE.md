# API Reference

This document provides a comprehensive reference for the Semantic Layer Pipeline's internal APIs and component interfaces.

## Table of Contents
1. [Configuration API](#configuration-api)
2. [Database Inspector API](#database-inspector-api)
3. [LLM Service API](#llm-service-api)
4. [Validation API](#validation-api)
5. [Orchestrator API](#orchestrator-api)
6. [Data Models](#data-models)
7. [Error Handling](#error-handling)

## Configuration API

### Class: `Config`
**Location**: `src/config.py`

The central configuration management class that loads settings from environment variables.

#### Constructor
```python
def __init__(self) -> None
```
Initializes configuration from environment variables.

#### Methods

##### `get_database_config() -> DatabaseConfig`
Returns database connection configuration.

**Returns**:
- `DatabaseConfig`: Database configuration object

**Example**:
```python
config = Config()
db_config = config.get_database_config()
print(db_config.connection_string)
```

##### `get_llm_config() -> LLMConfig`
Returns LLM provider configuration.

**Returns**:
- `LLMConfig`: LLM configuration object

##### `get_prompt_templates() -> Dict[str, str]`
Returns all prompt templates for LLM interactions.

**Returns**:
- `Dict[str, str]`: Dictionary of prompt templates keyed by template name

**Available Templates**:
- `entity_identification`: Phase 1 prompt for identifying business entities
- `entity_details`: Phase 2 prompt for generating detailed entity definitions
- `json_repair`: Prompt for fixing malformed JSON responses

##### `get_validation_settings() -> Dict[str, Any]`
Returns validation configuration settings.

**Returns**:
- `Dict[str, Any]`: Validation settings dictionary

### Class: `DatabaseConfig`
**Location**: `src/config.py`

Configuration dataclass for database settings.

#### Attributes
- `connection_string: str` - Database connection string
- `timeout: int = 30` - Connection timeout in seconds

### Class: `LLMConfig`
**Location**: `src/config.py`

Configuration dataclass for LLM settings.

#### Attributes
- `provider: str` - LLM provider ('openai' or 'anthropic')
- `model: str` - Model identifier
- `api_key: str` - API key for the provider
- `max_tokens: int = 4000` - Maximum tokens per response
- `temperature: float = 0.1` - Response creativity (0.0-1.0)
- `retry_attempts: int = 3` - Number of retry attempts
- `cache_enabled: bool = True` - Whether to cache responses

## Database Inspector API

### Class: `DatabaseInspector`
**Location**: `src/db_inspector.py`

Handles database introspection and metadata extraction.

#### Constructor
```python
def __init__(self, connection_string: str) -> None
```

**Parameters**:
- `connection_string: str` - Database connection string

#### Methods

##### `connect() -> None`
Establishes database connection.

**Raises**:
- `Exception`: If connection fails

##### `disconnect() -> None`
Closes database connection.

##### `get_table_names() -> List[str]`
Retrieves list of all table names.

**Returns**:
- `List[str]`: List of table names

##### `get_table_schema(table_name: str) -> List[ColumnInfo]`
Extracts complete schema information for a table.

**Parameters**:
- `table_name: str` - Name of the table

**Returns**:
- `List[ColumnInfo]`: List of column information objects

##### `get_foreign_key_relationships(table_name: str) -> List[Dict[str, str]]`
Gets foreign key relationships for a table.

**Parameters**:
- `table_name: str` - Name of the table

**Returns**:
- `List[Dict[str, str]]`: List of foreign key relationship dictionaries

##### `get_sample_data(table_name: str, limit: int = 5) -> List[Dict[str, Any]]`
Retrieves sample rows from a table.

**Parameters**:
- `table_name: str` - Name of the table
- `limit: int = 5` - Maximum number of rows to retrieve

**Returns**:
- `List[Dict[str, Any]]`: List of sample row dictionaries

##### `get_table_info(table_name: str) -> TableInfo`
Gets complete information about a table.

**Parameters**:
- `table_name: str` - Name of the table

**Returns**:
- `TableInfo`: Complete table information object

##### `extract_all_metadata() -> Dict[str, Any]`
Extracts all database metadata.

**Returns**:
- `Dict[str, Any]`: Complete database metadata dictionary

### Class: `ColumnInfo`
**Location**: `src/db_inspector.py`

Dataclass representing database column information.

#### Attributes
- `name: str` - Column name
- `data_type: str` - Column data type
- `is_nullable: bool` - Whether column allows NULL values
- `is_primary_key: bool` - Whether column is part of primary key
- `is_foreign_key: bool` - Whether column is a foreign key
- `foreign_table: Optional[str] = None` - Referenced table name
- `foreign_column: Optional[str] = None` - Referenced column name

### Class: `TableInfo`
**Location**: `src/db_inspector.py`

Dataclass representing complete table information.

#### Attributes
- `name: str` - Table name
- `columns: List[ColumnInfo]` - List of column information
- `primary_keys: List[str]` - List of primary key column names
- `foreign_keys: List[Dict[str, str]]` - List of foreign key relationships
- `sample_data: List[Dict[str, Any]]` - Sample data rows
- `row_count: int` - Total number of rows in table

## LLM Service API

### Class: `LLMService`
**Location**: `src/llm_service.py`

Main service for LLM interactions with caching and error handling.

#### Constructor
```python
def __init__(self, config: LLMConfig) -> None
```

**Parameters**:
- `config: LLMConfig` - LLM configuration object

#### Methods

##### `generate_entity_identification(schema_context: Dict[str, Any], business_context: str) -> Dict[str, Any]`
First LLM call: Identify core business entities from database schema.

**Parameters**:
- `schema_context: Dict[str, Any]` - Database schema information
- `business_context: str` - Business context documentation

**Returns**:
- `Dict[str, Any]` - Parsed JSON response with identified entities

**Raises**:
- `ValueError`: If LLM response cannot be parsed as valid JSON

##### `generate_entity_details(entity_name: str, entity_context: Dict[str, Any], schema_context: Dict[str, Any]) -> Dict[str, Any]`
Second LLM call: Generate detailed entity definition.

**Parameters**:
- `entity_name: str` - Name of the entity
- `entity_context: Dict[str, Any]` - Entity information from Phase 1
- `schema_context: Dict[str, Any]` - Database schema information

**Returns**:
- `Dict[str, Any]` - Parsed JSON response with entity details

**Raises**:
- `ValueError`: If LLM response cannot be parsed as valid JSON

### Abstract Class: `LLMProvider`
**Location**: `src/llm_service.py`

Abstract base class for LLM providers.

#### Methods

##### `generate_response(prompt: str, **kwargs) -> str`
Generate response from LLM provider.

**Parameters**:
- `prompt: str` - The prompt to send to the LLM
- `**kwargs` - Additional parameters (max_tokens, temperature, etc.)

**Returns**:
- `str` - Raw response from the LLM

### Class: `OpenAIProvider`
**Location**: `src/llm_service.py`

OpenAI API provider implementation.

#### Constructor
```python
def __init__(self, api_key: str, model: str) -> None
```

### Class: `AnthropicProvider`
**Location**: `src/llm_service.py`

Anthropic API provider implementation.

#### Constructor
```python
def __init__(self, api_key: str, model: str) -> None
```

### Class: `ResponseCache`
**Location**: `src/llm_service.py`

Simple file-based cache for LLM responses.

#### Constructor
```python
def __init__(self, cache_dir: str = ".cache") -> None
```

#### Methods

##### `get_cache_key(prompt: str, model: str) -> str`
Generate cache key from prompt and model.

##### `get_cached_response(cache_key: str) -> Optional[str]`
Retrieve cached response if available.

##### `cache_response(cache_key: str, response: str) -> None`
Store response in cache.

## Validation API

### Class: `ValidationOrchestrator`
**Location**: `src/validation.py`

Orchestrates all validation layers and manages feedback loops.

#### Constructor
```python
def __init__(self, db_inspector: DatabaseInspector, business_metrics: Dict[str, Any]) -> None
```

**Parameters**:
- `db_inspector: DatabaseInspector` - Database inspector instance
- `business_metrics: Dict[str, Any]` - Known business metrics for validation

#### Methods

##### `validate_semantic_layer(semantic_layer_json: Dict[str, Any]) -> Dict[str, Any]`
Run complete validation suite on semantic layer.

**Parameters**:
- `semantic_layer_json: Dict[str, Any]` - Generated semantic layer JSON

**Returns**:
- `Dict[str, Any]` - Comprehensive validation results

**Result Structure**:
```python
{
    "overall_valid": bool,
    "structural": {"valid": bool, "errors": List[str]},
    "sql": {"valid": bool, "errors": List[str], "failed_entities": List[str]},
    "semantic": {"valid": bool, "warnings": List[str]},
    "failed_entities": List[str],
    "validation_duration_seconds": float,
}
```

##### `generate_validation_report(results: Dict[str, Any]) -> str`
Generate human-readable validation report.

**Parameters**:
- `results: Dict[str, Any]` - Validation results from validate_semantic_layer

**Returns**:
- `str` - Formatted validation report

##### `get_failed_entities(validation_results: Dict[str, Any]) -> List[str]`
Extract list of entities that failed validation.

**Parameters**:
- `validation_results: Dict[str, Any]` - Validation results

**Returns**:
- `List[str]` - List of failed entity names

### Class: `StructuralValidator`
**Location**: `src/validation.py`

Validates JSON structure using Pydantic models.

#### Methods

##### `validate_semantic_layer(semantic_layer_json: Dict[str, Any]) -> Tuple[bool, List[str]]`
Validate complete semantic layer structure.

**Returns**:
- `Tuple[bool, List[str]]` - (is_valid, error_messages)

### Class: `SQLValidator`
**Location**: `src/validation.py`

Validates SQL syntax by executing test queries against database.

#### Constructor
```python
def __init__(self, db_inspector: DatabaseInspector) -> None
```

#### Methods

##### `validate_entity_sql(entity: EntityModel) -> Tuple[bool, List[str]]`
Validate SQL syntax for an entity's base query and attributes.

**Returns**:
- `Tuple[bool, List[str]]` - (is_valid, error_messages)

##### `test_query_execution(sql_query: str) -> Tuple[bool, Optional[str]]`
Test if a SQL query can be executed successfully.

**Returns**:
- `Tuple[bool, Optional[str]]` - (is_valid, error_message)

### Class: `SemanticValidator`
**Location**: `src/validation.py`

Validates semantic accuracy using business logic checks.

#### Constructor
```python
def __init__(self, db_inspector: DatabaseInspector, business_metrics: Dict[str, Any]) -> None
```

#### Methods

##### `validate_business_metrics(semantic_layer: SemanticLayerModel) -> List[str]`
Compare calculated metrics against known business values.

**Returns**:
- `List[str]` - List of warning messages

## Orchestrator API

### Class: `PipelineOrchestrator`
**Location**: `src/orchestrator.py`

Main orchestrator for the semantic layer generation pipeline.

#### Constructor
```python
def __init__(self, config: Config) -> None
```

**Parameters**:
- `config: Config` - Pipeline configuration

#### Methods

##### `run_pipeline(output_path: str = "output/semantic_layer.json") -> Dict[str, Any]`
Execute complete pipeline from start to finish.

**Parameters**:
- `output_path: str` - Path for output semantic layer JSON file

**Returns**:
- `Dict[str, Any]` - Pipeline execution results

**Result Structure**:
```python
{
    "success": bool,
    "execution_time": float,
    "entity_count": int,
    "valid_entity_count": int,
    "entity_names": List[str],
    "validation_passed": bool,
    "warnings": List[str],
    "output_path": str,
}
```

**Raises**:
- `Exception`: If pipeline execution fails

##### `initialize_components() -> None`
Initialize all pipeline components.

##### `extract_database_metadata() -> Dict[str, Any]`
Extract and cache database metadata.

##### `identify_business_entities() -> List[Dict[str, Any]]`
Use LLM to identify core business entities from schema.

##### `generate_entity_definitions(entities: List[Dict[str, Any]]) -> Dict[str, Any]`
Generate detailed definitions for each identified entity.

##### `validate_generated_layer(semantic_layer: Dict[str, Any]) -> Dict[str, Any]`
Run validation suite on generated semantic layer.

##### `handle_validation_failures(semantic_layer: Dict[str, Any], validation_results: Dict[str, Any]) -> Dict[str, Any]`
Attempt to fix entities that failed validation.

##### `save_semantic_layer(semantic_layer: Dict[str, Any], output_path: str) -> None`
Save final semantic layer to JSON file.

## Data Models

### Class: `SemanticLayerModel`
**Location**: `src/models.py`

Pydantic model for the complete semantic layer JSON structure.

#### Attributes
- `generated_at: datetime` - Generation timestamp
- `database: str` - Source database name
- `entities: Dict[str, EntityModel]` - Business entities

### Class: `EntityModel`
**Location**: `src/models.py`

Pydantic model for complete entity definition.

#### Attributes
- `description: str` - Entity description
- `base_query: str` - Base SQL query for the entity
- `attributes: Dict[str, AttributeModel]` - Entity attributes
- `relations: Dict[str, RelationModel]` - Entity relationships (optional)

#### Validators
- `validate_base_query`: Ensures base_query is a SELECT statement

### Class: `AttributeModel`
**Location**: `src/models.py`

Pydantic model for entity attribute definition.

#### Attributes
- `name: str` - Human-readable attribute name
- `description: str` - Description of the attribute
- `sql: str` - SQL expression for the attribute

### Class: `RelationModel`
**Location**: `src/models.py`

Pydantic model for entity relationship definition.

#### Attributes
- `name: str` - Human-readable relation name
- `description: str` - Description of the relationship
- `target_entity: str` - Target entity name
- `sql: str` - SQL join condition

## Error Handling

### Exception Types

#### Standard Python Exceptions
- `ValueError`: Invalid configuration or data format
- `RuntimeError`: Database connection or execution issues
- `ImportError`: Missing required dependencies
- `FileNotFoundError`: Missing configuration or data files

#### Custom Error Scenarios

##### Configuration Errors
```python
# Missing required environment variables
ValueError("API key not found for provider 'openai'")

# Invalid model configuration
ValueError("Unsupported LLM provider: unsupported_provider")
```

##### Database Errors
```python
# Connection failures
RuntimeError("Database connection not established")

# SQL execution errors
RuntimeError("Failed to execute query: table 'missing_table' not found")
```

##### LLM Service Errors
```python
# API communication failures
Exception("OpenAI API error: Rate limit exceeded")

# JSON parsing failures
ValueError("Unable to parse LLM response as valid JSON")
```

##### Validation Errors
```python
# Structural validation failures
ValidationError("field required: base_query")

# SQL validation failures
"Base query failed: syntax error near 'SELCT'"

# Semantic validation warnings
"Metric 'total_amount' value 1450 differs significantly from expected 1274"
```

### Error Handling Patterns

#### Retry with Exponential Backoff
```python
def _retry_with_backoff(self, func, *args, **kwargs):
    for attempt in range(self.config.retry_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == self.config.retry_attempts - 1:
                raise e
            wait_time = 2**attempt
            time.sleep(wait_time)
```

#### Graceful Degradation
```python
# Remove failed entities instead of failing entire pipeline
def handle_validation_failures(self, semantic_layer, validation_results):
    failed_entities = self.validator.get_failed_entities(validation_results)
    for entity_key in failed_entities:
        if entity_key in entities:
            del entities[entity_key]
    return semantic_layer
```

#### Comprehensive Error Reporting
```python
# Detailed error context in logs
self.logger.error(f"Entity {entity_name} failed SQL validation with {len(entity_errors)} errors")
for error in entity_errors:
    self.logger.error(f"  - {error}")
```

### Best Practices

1. **Always Log Errors**: Include context and error details in logs
2. **Graceful Fallbacks**: Provide partial functionality when possible
3. **User-Friendly Messages**: Translate technical errors to actionable messages
4. **Error Classification**: Distinguish between recoverable and fatal errors
5. **Resource Cleanup**: Ensure proper cleanup in finally blocks
6. **Validation Early**: Validate inputs early to prevent downstream errors

### Debugging Tips

1. **Enable Debug Logging**: Use `--log-level DEBUG` for detailed output
2. **Check Configuration**: Verify all environment variables are set correctly
3. **Test Database Connection**: Ensure database is accessible and has expected schema
4. **Validate API Keys**: Confirm API keys are valid and have sufficient quotas
5. **Review Cache**: Check `.cache` directory for cached responses during development
6. **Examine Output Files**: Review generated `schema_context.json` and `validation_report.txt`