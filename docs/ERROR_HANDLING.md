# Error Handling and Troubleshooting Guide

This guide provides comprehensive information about error handling, common issues, and troubleshooting strategies for the Semantic Layer Pipeline.

## Table of Contents
1. [Error Handling Philosophy](#error-handling-philosophy)
2. [Error Categories](#error-categories)
3. [Common Errors and Solutions](#common-errors-and-solutions)
4. [Debugging Strategies](#debugging-strategies)
5. [Recovery Mechanisms](#recovery-mechanisms)
6. [Best Practices](#best-practices)

## Error Handling Philosophy

The Semantic Layer Pipeline follows a **graceful degradation** approach to error handling:

1. **Fail Fast on Critical Issues**: Stop immediately for configuration or structural problems
2. **Continue with Warnings**: Process partial results when possible
3. **Detailed Error Reporting**: Provide actionable error messages and context
4. **Automatic Recovery**: Remove problematic entities and continue processing
5. **Comprehensive Logging**: Log all errors with context for debugging

## Error Categories

### 1. Configuration Errors

These occur during pipeline initialization due to missing or invalid configuration.

#### Severity: FATAL (Pipeline cannot start)

**Common Causes**:
- Missing environment variables
- Invalid API keys
- Incorrect database paths
- Unsupported model names

**Example Errors**:
```
ValueError: API key not found for provider 'openai'
ValueError: Unsupported LLM provider: invalid_provider
FileNotFoundError: Database file not found: /path/to/missing.db
```

**Resolution**:
1. Check `.env` file exists and contains required variables
2. Verify API keys are valid and have sufficient quota
3. Confirm database file path is correct and accessible

### 2. Database Connection Errors

These occur when the pipeline cannot connect to or query the database.

#### Severity: FATAL (Cannot extract metadata)

**Common Causes**:
- Database file doesn't exist
- Insufficient file permissions
- Corrupted database file
- Unsupported database format

**Example Errors**:
```
RuntimeError: Database connection not established
sqlite3.OperationalError: database is locked
sqlite3.DatabaseError: file is not a database
```

**Resolution**:
1. Verify database file exists and is readable
2. Check file permissions (read access required)
3. Test database integrity with SQLite tools
4. Ensure no other processes are locking the database

### 3. LLM API Errors

These occur during communication with LLM providers.

#### Severity: RECOVERABLE (Retry mechanisms available)

**Common Causes**:
- Rate limiting
- Invalid API keys
- Network connectivity issues
- Model availability problems
- Quota exceeded

**Example Errors**:
```
openai.RateLimitError: Rate limit exceeded
anthropic.AuthenticationError: Invalid API key
requests.exceptions.ConnectionError: Failed to establish connection
```

**Resolution**:
1. Check API key validity and permissions
2. Verify account quota and billing status
3. Test network connectivity
4. Wait and retry for temporary rate limits

### 4. JSON Parsing Errors

These occur when LLM responses cannot be parsed as valid JSON.

#### Severity: RECOVERABLE (JSON repair mechanisms available)

**Common Causes**:
- LLM returns malformed JSON
- Response wrapped in markdown
- Incomplete responses due to token limits
- Special characters in JSON strings

**Example Errors**:
```
json.JSONDecodeError: Expecting ',' delimiter: line 5 column 10
ValueError: Unable to parse LLM response as valid JSON
```

**Resolution**:
1. Automatic JSON repair prompts
2. Markdown extraction for wrapped JSON
3. Increase max_tokens if responses are truncated
4. Review LLM prompts for clarity

### 5. SQL Validation Errors

These occur when generated SQL cannot be executed against the database.

#### Severity: RECOVERABLE (Failed entities are removed)

**Common Causes**:
- Syntax errors in generated SQL
- References to non-existent tables or columns
- Invalid join conditions
- Complex aggregations with errors

**Example Errors**:
```
sqlite3.OperationalError: no such table: NonExistentTable
sqlite3.OperationalError: syntax error near 'SELCT'
sqlite3.OperationalError: no such column: missing_column
```

**Resolution**:
1. Automatic entity removal for failed SQL
2. Review database schema consistency
3. Check LLM prompts for SQL generation guidance
4. Validate table and column references

### 6. Validation Errors

These occur during the multi-layer validation process.

#### Severity: WARNING (Semantic issues) or RECOVERABLE (Structural issues)

**Common Causes**:
- Missing required fields in entity definitions
- Invalid data types in generated JSON
- Business metrics that don't align with expectations
- Cardinality issues in query results

**Example Errors**:
```
ValidationError: field required: base_query
ValidationError: base_query must be a SELECT statement
Warning: Metric 'total_amount' differs significantly from expected value
```

**Resolution**:
1. Automatic structural validation with Pydantic
2. Entity removal for structural failures
3. Warning generation for semantic issues
4. Manual review of business logic warnings

## Common Errors and Solutions

### Error: "ModuleNotFoundError: No module named 'openai'"

**Cause**: Missing Python dependencies

**Solution**:
```bash
pip install -r requirements.txt
```

### Error: "Database connection not established"

**Cause**: Database path incorrect or file permissions

**Solution**:
```bash
# Check file exists
ls -la tests/northwind.db

# Check file permissions
chmod 644 tests/northwind.db

# Test database manually
sqlite3 tests/northwind.db ".tables"
```

### Error: "API key not found for provider 'openai'"

**Cause**: Missing or incorrect environment variable

**Solution**:
```bash
# Check .env file
cat .env

# Verify API key variable name
export OPENAI_API_KEY="your-key-here"

# Or for Anthropic
export ANTHROPIC_API_KEY="your-key-here"
```

### Error: "Rate limit exceeded"

**Cause**: Too many API requests in short time

**Solution**:
```bash
# Enable caching to reduce API calls
export CACHE_ENABLED=true

# Reduce retry attempts
export MAX_RETRY_ATTEMPTS=1

# Wait and retry later
# The pipeline includes automatic exponential backoff
```

### Error: "Unable to parse LLM response as valid JSON"

**Cause**: LLM returned malformed JSON

**Solution**:
1. The pipeline automatically attempts JSON repair
2. Check if max_tokens is sufficient for complete responses
3. Review generated responses in cache files (`.cache` directory)
4. Consider adjusting temperature for more consistent output

### Error: "Base query failed: syntax error"

**Cause**: Generated SQL has syntax errors

**Solution**:
1. Failed entities are automatically removed
2. Review entity identification to ensure relevant tables are included
3. Check database schema for any inconsistencies
4. Examine generated SQL in debug logs

### Error: "Entity query returns no results"

**Cause**: Generated query doesn't match actual data

**Solution**:
1. Review join conditions in base query
2. Check if tables have data
3. Verify foreign key relationships are correct
4. Consider this a semantic warning, not a failure

## Debugging Strategies

### 1. Enable Debug Logging

```bash
python main.py --log-level DEBUG
```

This provides detailed information about:
- Configuration loading
- Database connection details
- LLM request/response details
- SQL query execution
- Validation steps and results

### 2. Examine Generated Files

The pipeline creates several debug files:

```bash
# Schema context (database metadata)
cat output/schema_context.json

# Validation report
cat output/validation_report.txt

# Pipeline execution report
cat output/pipeline_report.txt

# Log files (timestamped)
cat pipeline_20241117_*.log
```

### 3. Check Cache Contents

When caching is enabled, examine cached responses:

```bash
# List cached LLM responses
ls -la .cache/

# Examine specific cached response
cat .cache/[hash].json
```

### 4. Test Components Individually

Test individual components for isolation:

```python
# Test database connection
from src.db_inspector import DatabaseInspector
inspector = DatabaseInspector("tests/northwind.db")
inspector.connect()
print(inspector.get_table_names())

# Test LLM service
from src.llm_service import LLMService
from src.config import Config
config = Config()
llm = LLMService(config.llm_config)
# Test with simple prompt
```

### 5. Validate Configuration

```python
# Test configuration loading
from src.config import Config
try:
    config = Config()
    print("Configuration loaded successfully")
    print(f"LLM Provider: {config.llm_config.provider}")
    print(f"Database: {config.database_config.connection_string}")
except Exception as e:
    print(f"Configuration error: {e}")
```

## Recovery Mechanisms

### 1. Automatic Retry with Exponential Backoff

The pipeline automatically retries failed API calls:

```python
# Configurable retry attempts
MAX_RETRY_ATTEMPTS=3  # Default

# Exponential backoff: 1s, 2s, 4s delays
wait_time = 2**attempt
```

### 2. Failed Entity Removal

Entities that fail validation are automatically removed:

```python
def handle_validation_failures(self, semantic_layer, validation_results):
    failed_entities = self.validator.get_failed_entities(validation_results)

    for entity_key in failed_entities:
        if entity_key in entities:
            self.logger.warning(f"Removing failed entity: {entity_key}")
            del entities[entity_key]

    return semantic_layer
```

### 3. JSON Repair

The pipeline attempts to repair malformed JSON:

```python
def _extract_json_from_markdown(self, response: str) -> str:
    # Extract JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(json_pattern, response, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return response
```

### 4. Graceful Degradation

The pipeline continues with partial results:

- Failed entities are removed, successful ones are kept
- Warnings are generated for semantic issues
- Pipeline completes with available entities

### 5. Cache-Based Recovery

Cached responses provide resilience:

- Reduces API dependency during development
- Provides consistent results for testing
- Allows pipeline restart without re-processing

## Best Practices

### 1. Configuration Management

```bash
# Always use .env file for configuration
cp .env.example .env

# Keep API keys secure
chmod 600 .env

# Use different configurations for different environments
# .env.development, .env.production, etc.
```

### 2. Error Monitoring

```bash
# Monitor error patterns in logs
grep "ERROR" pipeline_*.log

# Check validation failure rates
grep "Failed entities" pipeline_*.log

# Monitor API usage
grep "Token usage" pipeline_*.log
```

### 3. Resource Management

```bash
# Enable caching for development
CACHE_ENABLED=true

# Monitor cache size
du -sh .cache/

# Clean cache when needed
rm -rf .cache/*
```

### 4. Testing Strategy

```bash
# Test with minimal configuration first
python main.py --log-level INFO

# Enable debug for troubleshooting
python main.py --log-level DEBUG

# Test without cache for consistency
python main.py --no-cache
```

### 5. Performance Optimization

```bash
# Reduce LLM tokens for faster testing
export MAX_TOKENS=2000

# Lower temperature for more consistent results
export TEMPERATURE=0.05

# Increase retry attempts for production
export MAX_RETRY_ATTEMPTS=5
```

## Emergency Procedures

### 1. Pipeline Stuck or Hanging

**Symptoms**: Pipeline doesn't progress, no log output

**Actions**:
1. Check network connectivity
2. Verify API service status
3. Kill process and restart with debug logging
4. Check database locks

### 2. Memory Issues

**Symptoms**: Out of memory errors, system slowdown

**Actions**:
1. Check cache directory size
2. Reduce max_tokens setting
3. Clear cache if necessary
4. Monitor system resources

### 3. API Quota Exceeded

**Symptoms**: Consistent rate limit or quota errors

**Actions**:
1. Enable caching to reduce API calls
2. Check API account billing/limits
3. Use different API provider if available
4. Wait for quota reset

### 4. Database Corruption

**Symptoms**: Database connection errors, invalid data

**Actions**:
1. Create backup of database file
2. Test database integrity with SQLite tools
3. Restore from backup if necessary
4. Check for disk space/permissions

### 5. Complete System Failure

**Symptoms**: Multiple component failures, unclear errors

**Actions**:
1. Start fresh with clean environment
2. Verify all dependencies are installed
3. Test each component individually
4. Check system resources and permissions
5. Review recent changes to configuration

## Support and Resources

### Log File Analysis

The pipeline generates comprehensive logs for analysis:

- **Console Output**: Real-time progress and summary
- **File Logs**: Detailed debug information with timestamps
- **Validation Reports**: Structured validation results
- **Pipeline Reports**: Overall execution summary

### Documentation References

- [Configuration Guide](CONFIGURATION_GUIDE.md): Detailed configuration options
- [API Reference](API_REFERENCE.md): Complete API documentation
- [LLM Strategy](LLM_STRATEGY.md): LLM prompting and error handling
- [Validation Framework](VALIDATION_AND_ACCURACY.md): Validation error details

### Community Support

For additional support:
1. Check existing issues in the project repository
2. Create detailed bug reports with log files
3. Include configuration (without API keys) and error messages
4. Provide steps to reproduce the issue

Remember: The pipeline is designed to be resilient and provide useful output even when some components fail. Focus on understanding the warnings and partial results rather than achieving perfect execution on the first try.