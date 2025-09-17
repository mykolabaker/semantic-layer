# Configuration Guide

This guide provides detailed instructions for configuring the Semantic Layer Pipeline for different environments and use cases.

## Environment Variables

The pipeline is configured entirely through environment variables, which should be defined in a `.env` file in the project root.

### Required Configuration

#### Database Configuration

```bash
# Database connection string
DATABASE_CONNECTION_STRING=sqlite:///path/to/northwind.db
# Or for SQLite file path directly:
DATABASE_CONNECTION_STRING=tests/northwind.db

# Database timeout in seconds (optional)
DATABASE_TIMEOUT=30
```

#### LLM Provider Configuration

Choose either OpenAI or Anthropic:

**For OpenAI:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key-here
LLM_MODEL=gpt-4-turbo-preview
```

**For Anthropic:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
LLM_MODEL=claude-3-sonnet-20240229
```

### Optional Configuration

#### LLM Parameters

```bash
# Maximum tokens for LLM response (default: 4000)
MAX_TOKENS=4000

# Temperature for LLM creativity (0.0-1.0, default: 0.1)
TEMPERATURE=0.1

# Number of retry attempts for failed API calls (default: 3)
MAX_RETRY_ATTEMPTS=3
```

#### Caching Configuration

```bash
# Enable/disable LLM response caching (default: true)
CACHE_ENABLED=true
```

#### Validation Configuration

```bash
# Enable/disable validation (default: true)
VALIDATION_ENABLED=true
```

## Configuration Management

The configuration is managed through the `Config` class in `src/config.py`. The system supports:

1. **Environment Variable Loading**: Automatic loading from `.env` file
2. **Default Values**: Sensible defaults for optional parameters
3. **Type Conversion**: Automatic conversion of string environment variables to appropriate types
4. **Validation**: Basic validation of required parameters

## Example Configurations

### Development Environment

```bash
# .env for development
DATABASE_CONNECTION_STRING=tests/northwind.db
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4-turbo-preview
MAX_TOKENS=4000
TEMPERATURE=0.1
CACHE_ENABLED=true
MAX_RETRY_ATTEMPTS=3
```

### Production Environment

```bash
# .env for production
DATABASE_CONNECTION_STRING=sqlite:///data/production/northwind.db
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_MODEL=claude-3-sonnet-20240229
MAX_TOKENS=6000
TEMPERATURE=0.05
CACHE_ENABLED=false
MAX_RETRY_ATTEMPTS=5
VALIDATION_ENABLED=true
```

### Testing Environment

```bash
# .env for testing
DATABASE_CONNECTION_STRING=tests/northwind.db
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-test-key-here
LLM_MODEL=gpt-3.5-turbo
MAX_TOKENS=2000
TEMPERATURE=0.0
CACHE_ENABLED=true
MAX_RETRY_ATTEMPTS=1
```

## Configuration Validation

The pipeline performs validation checks at startup:

1. **Required Variables**: Ensures all required environment variables are present
2. **API Key Validation**: Checks that the appropriate API key is provided for the selected LLM provider
3. **Database Connectivity**: Tests database connection during initialization
4. **Model Compatibility**: Validates that the specified model is supported by the provider

## Business Metrics Configuration

The pipeline includes predefined business metrics for validation in `src/config.py`:

```python
business_metrics = {
    "average_order_value": 1274,
    "average_items_per_order": 2.6,
    "total_orders": 830,
    "total_customers": 91,
    "total_products": 77,
    "total_employees": 9,
    "customer_retention_rate": 0.89,
    "average_fulfillment_days": 8,
}
```

These metrics are used during semantic validation to ensure generated entities produce reasonable business values.

## Troubleshooting Configuration Issues

### Common Issues

1. **Missing API Keys**: Ensure the correct API key environment variable is set for your chosen LLM provider
2. **Database Connection**: Verify the database file exists and is accessible
3. **Model Names**: Check that the model name is correctly specified and supported by your LLM provider
4. **Cache Directory**: Ensure the `.cache` directory is writable if caching is enabled

### Debug Mode

To troubleshoot configuration issues, run the pipeline with debug logging:

```bash
python main.py --log-level DEBUG
```

This will output detailed configuration information during startup, including:
- Database connection details
- LLM provider and model information
- Cache settings
- Validation configuration

### Configuration Testing

To test your configuration without running the full pipeline, you can use the `config.py` module directly:

```bash
python -c "from src.config import Config; c = Config(); print('Configuration loaded successfully')"
```

This will validate your configuration and report any issues.