# Semantic Layer Pipeline

An automated Python pipeline that analyzes the Northwind database and generates a comprehensive semantic layer using LLM APIs.

## Overview

This pipeline uses a sophisticated two-phase LLM strategy to understand database structure and generate business-meaningful entities:

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

See `.env.example` for all configuration options including:
- Database connection settings
- LLM provider and model selection
- Pipeline behavior parameters

## Output

The pipeline generates `output/semantic_layer.json` containing 5-7 core business entities with:
- Human-readable descriptions
- Optimized base queries
- Business-relevant attributes
- Entity relationships

## Architecture

- `src/config.py` - Configuration management
- `src/db_inspector.py` - Database introspection
- `src/llm_service.py` - LLM API interactions with caching
- `src/validation.py` - Multi-layered validation system
- `src/orchestrator.py` - Pipeline coordination
- `src/models.py` - Pydantic data models

## Documentation

See `docs/methodology.md` for detailed explanation of:
- LLM prompting strategies
- Validation methodology
- Design decisions and assumptions

## License

MIT License
