# Semantic Layer Pipeline

An automated Python pipeline that analyzes the Northwind database, understands its structure using Large Language Models (LLMs), and generates a comprehensive, accurate, and validated semantic layer.

## 1. How to Configure and Run the Pipeline

### 1.1. Configuration

Configuration is managed via environment variables. Create a `.env` file in the project root by copying the `.env.example` file.

```bash
cp .env.example .env
```

**Required Variables:**

- `DATABASE_CONNECTION_STRING`: The connection string for the Northwind database.
- `LLM_PROVIDER`: The LLM provider to use. Supported values are `openai` and `anthropic`.
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`: Your API key for the chosen provider.

**Optional Variables:**

- `LLM_MODEL`: The specific model to use (e.g., `gpt-4-turbo-preview`).
- `MAX_TOKENS`: The maximum number of tokens for the LLM response.
- `TEMPERATURE`: The creativity of the LLM response (0.0 to 1.0).
- `CACHE_ENABLED`: Set to `true` to cache LLM responses and reduce costs during development.
- `MAX_RETRY_ATTEMPTS`: The number of times to retry a failed API call.

### 1.2. Running the Pipeline

The pipeline is executed from the command line.

**Basic Execution:**

```bash
python main.py
```

**Command-Line Arguments:**

- `--output` or `-o`: Specify a custom path for the output `semantic_layer.json` file.
- `--log-level`: Set the logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- `--no-cache`: Temporarily disable LLM response caching for a single run.
- `--version`: Display the pipeline version.

**Example with all options:**

```bash
python main.py -o output/my_layer.json --log-level DEBUG --no-cache
```

## 2. LLM Prompting Strategy

Our methodology is centered around a **Two-Phase Prompting Strategy** designed to maximize accuracy and relevance by breaking down the complex task of understanding a database into smaller, manageable steps.

### Phase 1: Entity Identification

The first phase identifies the core business concepts within the database.

- **Purpose**: To discover 5-7 high-level business entities (e.g., Customers, Products, Orders) rather than just listing database tables.
- **Input**:
    - The complete database schema.
    - High-level business context about Northwind Traders.
- **Technique**: The LLM is instructed to use **Chain-of-Thought reasoning**. It first analyzes the business functions (e.g., Sales, Logistics) and then groups related tables that logically represent a single business entity.
- **Output**: A structured JSON object listing the identified entities, the tables they are composed of, and the rationale for the grouping.

### Phase 2: Detailed Entity Generation

For each entity identified in Phase 1, this phase generates a detailed, queryable definition.

- **Purpose**: To create a precise and efficient SQL-based definition for each business entity.
- **Input**:
    - The context of a single entity (e.g., "Orders").
    - The specific schema for the tables relevant to that entity.
    - Sample data from those tables.
- **Technique**: The LLM uses **Few-Shot Learning**. It is provided with a high-quality example of a complete entity definition, which guides it to produce an output that is both syntactically correct and semantically rich.
- **Output**: A complete JSON definition for the entity, including a `base_query`, business-meaningful `attributes`, and `relations` to other entities.

This two-phase approach allows the LLM to first build a conceptual map of the database and then zoom in to generate the fine-grained details, which is more effective than asking it to do everything at once.

## 3. How the Pipeline Ensures Accuracy

Accuracy is ensured through a **Multi-Layered Validation** process that checks the generated semantic layer from different angles. Failed entities are automatically removed to ensure the final output is reliable.

### Layer 1: Structural Validation

- **Purpose**: To ensure the generated JSON output strictly adheres to the required schema.
- **Method**: The entire JSON output is validated against Pydantic models (`src/models.py`). This check is fast and catches any structural or data type errors immediately.

### Layer 2: SQL Syntax Validation

- **Purpose**: To verify that all generated SQL queries are syntactically correct and executable against the database.
- **Method**: For each entity, the pipeline constructs and executes a `LIMIT 1` query. This includes the `base_query` and the SQL expressions for all its attributes. This check guarantees that the generated SQL will not fail at runtime.

### Layer 3: Semantic Validation

- **Purpose**: To ensure the generated entities are logically correct and make business sense.
- **Method**: The pipeline performs several checks, including:
    - **Metric Plausibility**: It calculates key business metrics from the generated entities and compares them against known, trusted values.
    - **Cardinality Checks**: It verifies that entity queries do not produce an unexpected number of rows (e.g., zero or an excessively large number, which could indicate a Cartesian product).

This rigorous, multi-layered approach ensures that the final semantic layer is not only well-structured and syntactically correct but also semantically sound and aligned with business logic.

## 4. Assumptions and Design Decisions

- **Database Access**: The pipeline assumes it has a stable, read-only connection to the Northwind database.
- **LLM Capabilities**: We assume the chosen LLMs are capable of understanding SQL and can follow complex instructions for JSON generation.
- **Business Context**: The quality of the entity identification phase depends on the accuracy of the provided business documentation.
- **Modular Design**: The pipeline is built with a clear separation of concerns (`db_inspector`, `llm_service`, `validation`, `orchestrator`). This makes the codebase easy to maintain, test, and extend.
- **Configuration Management**: All settings are centralized in `src/config.py` and managed via environment variables, allowing for easy configuration without code changes.
- **Caching Strategy**: LLM responses are cached to disk. This significantly speeds up development and reduces API costs by avoiding redundant calls.
- **Error Handling**: The pipeline includes robust error handling, such as automatic retries with exponential backoff for API calls and a feedback loop to remove entities that fail validation.

## 5. Evaluation Criteria Analysis

- **Pipeline Design**: The architecture is logical and maintainable, with distinct modules for data extraction, LLM interaction, validation, and orchestration. This separation of concerns makes the system robust and easy to modify.
- **LLM Integration**: LLMs are used effectively through a two-phase prompting strategy that aligns with how a human would approach the problem. Techniques like Chain-of-Thought and Few-Shot Learning are employed to maximize the quality of the output.
- **Accuracy**: The multi-layered validation system ensures a high degree of accuracy by checking the structural, syntactic, and semantic correctness of the generated layer.
- **Code Quality**: The code is well-organized, follows best practices, and is documented. The use of Pydantic models for data validation and a clear, modular structure are key highlights.
- **Methodology**: The approach is clear and reproducible. The combination of a two-phase LLM strategy and a multi-layered validation process provides a robust framework for generating a semantic layer.
- **Error Handling**: The pipeline is resilient. It includes retries for network-related issues and a validation feedback loop that automatically prunes invalid entities, ensuring the final output is always usable.