# Semantic Layer Pipeline

An automated Python pipeline that analyzes the Northwind database and generates a comprehensive semantic layer using LLM
APIs.

## Overview

This pipeline uses a sophisticated two-phase LLM strategy to understand database structure and generate
business-meaningful entities:

1. **Entity Identification**: Analyze complete schema to identify core business entities
2. **Detailed Generation**: Generate precise SQL definitions for each entity

## Features

- Multi-layered validation (structural, SQL syntax, semantic accuracy)
- LLM response caching for cost efficiency
- Comprehensive error handling with automatic retry
- Modular, maintainable architecture following SOLID principles

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd semantic_layer_pipeline
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the pipeline**
   ```bash
   python main.py
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_CONNECTION_STRING="your_database_connection_string"
DATABASE_TIMEOUT=30

# LLM Configuration
LLM_PROVIDER=openai  # or 'anthropic'
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Pipeline Settings
CACHE_ENABLED=true
MAX_RETRY_ATTEMPTS=3
VALIDATION_ENABLED=true
```

## Usage

```bash
# Basic usage
python main.py

# Specify custom output path
python main.py --output my_semantic_layer.json

# Enable debug logging
python main.py --log-level DEBUG

# Disable caching
python main.py --no-cache
```

## Output

The pipeline generates several outputs in the `output/` directory:

- `semantic_layer.json` - Main semantic layer definition
- `schema_context.json` - Extracted database metadata
- `validation_report.txt` - Detailed validation results
- `pipeline_report.txt` - Execution summary

## Architecture

The pipeline follows a modular architecture with clear separation of concerns:

- **`src/config.py`** - Configuration management and prompt templates
- **`src/db_inspector.py`** - Database introspection and metadata extraction
- **`src/llm_service.py`** - LLM API interactions with caching
- **`src/validation.py`** - Multi-layered validation system
- **`src/orchestrator.py`** - Pipeline coordination and workflow
- **`src/models.py`** - Pydantic data models for validation

## Methodology

### Two-Phase LLM Strategy

1. **Entity Identification Phase**
    - Analyzes complete database schema with business context
    - Identifies 5-7 core business entities
    - Uses chain-of-thought reasoning to group related tables

2. **Entity Generation Phase**
    - Generates detailed SQL definitions for each entity
    - Creates business-meaningful attributes and relationships
    - Uses few-shot learning with detailed examples

### Multi-Layer Validation

1. **Structural Validation** - Pydantic model validation
2. **SQL Syntax Validation** - Database query execution tests
3. **Semantic Validation** - Business metric comparison

## Error Handling

- Exponential backoff retry for API failures
- JSON repair mechanism for malformed LLM responses
- Automatic removal of entities that fail validation
- Comprehensive logging throughout execution

## Cost Optimization

- File-based caching of LLM responses
- Efficient prompt design to minimize token usage
- Configurable retry limits and timeouts

## Documentation

See `docs/methodology.md` for detailed explanation of:

- LLM prompting strategies and templates
- Validation methodology and business rules
- Design decisions and assumptions
- Performance considerations

## Requirements

- Python 3.8+
- OpenAI or Anthropic API key
- Access to Northwind database (SQLite Cloud)

## License

MIT License
