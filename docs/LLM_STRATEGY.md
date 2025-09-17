# LLM Prompting Strategy Deep Dive

This document provides a comprehensive explanation of the Large Language Model (LLM) prompting strategy used in the Semantic Layer Pipeline.

## Overview

The pipeline employs a sophisticated **Two-Phase Prompting Strategy** combined with advanced prompt engineering techniques to transform raw database schemas into meaningful business-oriented semantic layers.

## Phase 1: Entity Identification

### Objective
Identify 5-7 core business entities that represent meaningful business concepts rather than simply listing database tables.

### Prompt Engineering Techniques

#### 1. Chain-of-Thought Reasoning
The prompt explicitly guides the LLM through a step-by-step reasoning process:

```
Think step-by-step:
1. First, understand the primary business processes
2. Identify which tables work together to represent complete business concepts
3. Group related tables into logical business entities
4. Ensure entities represent end-user business value, not just database tables
```

This structured approach helps the LLM make more coherent and logical groupings.

#### 2. Rich Context Provision
The prompt includes multiple context layers:

- **Database Schema**: Complete table structure, columns, relationships, and sample data
- **Business Context**: High-level business documentation about Northwind Traders
- **Functional Areas**: Explicit mention of key business functions (Product Sourcing, Sales, Logistics)

#### 3. Output Format Specification
The prompt uses a detailed JSON schema specification:

```json
{
    "entities": [
        {
            "name": "entity_key_name",
            "display_name": "Human Readable Name",
            "description": "What this entity represents in business terms",
            "primary_tables": ["table1", "table2"],
            "business_function": "Which core business function this supports",
            "rationale": "Why these tables form a coherent business entity"
        }
    ]
}
```

### Prompt Template Analysis

The entity identification prompt template (`config.py:74-110`) employs several key strategies:

1. **Role Assignment**: "You are an expert data analyst" establishes context and expertise
2. **Task Decomposition**: Breaks down the complex task into manageable steps
3. **Business Focus**: Emphasizes business value over technical database structure
4. **Constraint Specification**: Requests 5-7 entities to ensure focus on core concepts

## Phase 2: Detailed Entity Generation

### Objective
Generate precise, SQL-based definitions for each identified business entity with optimized queries and business-meaningful attributes.

### Prompt Engineering Techniques

#### 1. Few-Shot Learning
The prompt provides a comprehensive example of a complete entity definition:

```json
{
    "description": "Customer order transactions including details and totals",
    "base_query": "SELECT o.OrderID, o.CustomerID, o.OrderDate, c.CompanyName FROM Orders o JOIN Customers c ON o.CustomerID = c.CustomerID",
    "attributes": {
        "order_id": {
            "name": "Order ID",
            "description": "Unique identifier for each order",
            "sql": "o.OrderID"
        },
        "total_amount": {
            "name": "Total Order Amount",
            "description": "Total order value after discounts",
            "sql": "COALESCE(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 0)"
        }
    },
    "relations": {
        "customer": {
            "name": "Customer",
            "description": "Customer who placed the order",
            "target_entity": "customers",
            "sql": "o.CustomerID = c.CustomerID"
        }
    }
}
```

This example teaches the LLM the expected structure, style, and quality level.

#### 2. Context Filtering
For each entity, the prompt provides only relevant schema information:

- **Focused Schema**: Only tables relevant to the specific entity
- **Sample Data**: Real data samples to understand data patterns
- **Entity Context**: Information from Phase 1 about the entity's purpose

#### 3. SQL Quality Requirements
The prompt explicitly specifies SQL quality requirements:

- Use efficient JOINs and avoid Cartesian products
- Create user-friendly attribute names
- Include relevant business metrics
- Ensure SQL is syntactically correct

### Prompt Template Analysis

The entity details prompt template (`config.py:111-165`) includes:

1. **Contextual Grounding**: Provides entity-specific context from Phase 1
2. **Example-Driven Learning**: Shows a complete, high-quality example
3. **Quality Constraints**: Explicit requirements for SQL optimization and business relevance
4. **Structured Output**: Clear JSON schema with required fields

## Advanced Prompt Engineering Features

### 1. JSON Repair Capability
The system includes a specialized JSON repair prompt (`config.py:166-172`) to handle malformed LLM responses:

```
The following JSON response has syntax errors. Please fix the JSON syntax while preserving all the content:

MALFORMED JSON:
{malformed_json}

Return only the corrected JSON with proper syntax.
```

### 2. Response Processing Pipeline
The LLM service includes sophisticated response processing:

```python
# Extract JSON from markdown code blocks
if "```json" in response:
    cleaned_response = self._extract_json_from_markdown(response)

# Parse and validate JSON
parsed_response = json.loads(cleaned_response)
```

### 3. Caching Strategy
The system implements intelligent caching based on:
- Prompt content
- Model type
- SHA256 hash for cache keys

This reduces API costs and improves development speed.

## Provider-Specific Implementations

### OpenAI Integration
```python
response = self.client.chat.completions.create(
    model=self.model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=max_tokens,
    temperature=temperature,
)
```

### Anthropic Integration
```python
response = self.client.messages.create(
    model=self.model,
    max_tokens=max_tokens,
    temperature=temperature,
    messages=[{"role": "user", "content": prompt}],
)
```

## Error Handling and Resilience

### 1. Exponential Backoff Retry
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

### 2. JSON Parsing Fallbacks
- Primary: Direct JSON parsing
- Fallback 1: Extract from markdown code blocks
- Fallback 2: JSON repair prompt
- Final: Graceful error handling

### 3. Token Management
- Prompt length monitoring
- Warning for large prompts (>100,000 characters)
- Token usage tracking and logging

## Performance Optimizations

### 1. Context Optimization
- Schema filtering to include only relevant tables
- Sample data limiting (3 rows per table for LLM context)
- Structured JSON serialization

### 2. Response Caching
- File-based cache with SHA256 keys
- Configurable cache enable/disable
- Development-time cost reduction

### 3. Parallel Processing
The orchestrator processes entities sequentially but optimizes within each phase:
- Batch schema extraction
- Efficient database queries
- Streamlined validation

## Quality Assurance

### 1. Prompt Testing
- Comprehensive logging of prompt generation
- Response quality monitoring
- Token usage tracking

### 2. Output Validation
- Immediate JSON schema validation
- SQL syntax testing
- Business logic verification

### 3. Iterative Improvement
- Failed entity handling and removal
- Validation feedback loops
- Continuous quality monitoring

## Future Enhancements

### Potential Improvements
1. **Dynamic Prompt Adaptation**: Adjust prompts based on database complexity
2. **Multi-Model Ensemble**: Use different models for different phases
3. **Active Learning**: Improve prompts based on validation feedback
4. **Context Window Optimization**: Better management of large schemas
5. **Streaming Responses**: Handle very large outputs more efficiently

### Experimental Features
1. **Chain-of-Thought Validation**: Have LLM validate its own outputs
2. **Self-Correcting Loops**: Automatic prompt refinement based on errors
3. **Domain-Specific Prompts**: Specialized prompts for different industries
4. **Multi-Language Support**: Generate semantic layers in multiple languages

This LLM strategy represents a sophisticated approach to automated semantic layer generation, combining proven prompt engineering techniques with robust error handling and quality assurance mechanisms.