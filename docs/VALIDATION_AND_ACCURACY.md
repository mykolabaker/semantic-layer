# Validation and Accuracy Framework

This document provides a comprehensive overview of how the Semantic Layer Pipeline ensures accuracy through its multi-layered validation system.

## Overview

The pipeline implements a **Three-Layer Validation Architecture** that progressively validates the generated semantic layer from structural correctness to business logic accuracy. This approach ensures that the final output is not only syntactically correct but also semantically meaningful and business-ready.

## Validation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Validation Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Structural Validation (Pydantic Models)          │
│  ↓                                                          │
│  Layer 2: SQL Syntax Validation (Database Execution)       │
│  ↓                                                          │
│  Layer 3: Semantic Validation (Business Logic)             │
├─────────────────────────────────────────────────────────────┤
│                   Feedback & Repair                        │
│  • Failed Entity Removal                                   │
│  • Re-validation After Fixes                               │
│  • Comprehensive Reporting                                 │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: Structural Validation

### Purpose
Ensures the generated JSON output strictly adheres to the required schema and data types.

### Implementation
Located in `src/validation.py:12-53`, the `StructuralValidator` class uses Pydantic models for validation:

```python
def validate_semantic_layer(self, semantic_layer_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    try:
        semantic_layer_model = SemanticLayerModel(**semantic_layer_json)
        return True, []
    except Exception as e:
        return False, [f"Structural validation failed: {str(e)}"]
```

### Validation Rules
The system validates against these Pydantic models (`src/models.py`):

#### SemanticLayerModel
- `generated_at`: DateTime timestamp
- `database`: String database identifier
- `entities`: Dictionary of EntityModel objects

#### EntityModel
- `description`: String description of the entity
- `base_query`: SQL SELECT statement (validated to start with "SELECT")
- `attributes`: Dictionary of AttributeModel objects
- `relations`: Dictionary of RelationModel objects (optional)

#### AttributeModel
- `name`: Human-readable attribute name
- `description`: Attribute description
- `sql`: SQL expression for the attribute

#### RelationModel
- `name`: Human-readable relation name
- `description`: Relationship description
- `target_entity`: Target entity name
- `sql`: SQL join condition

### Error Handling
- Detailed Pydantic validation error reporting
- Location-specific error messages
- Graceful handling of nested validation failures

## Layer 2: SQL Syntax Validation

### Purpose
Verifies that all generated SQL queries are syntactically correct and executable against the database.

### Implementation
The `SQLValidator` class (`src/validation.py:55-198`) performs comprehensive SQL testing:

```python
def validate_entity_sql(self, entity: EntityModel) -> Tuple[bool, List[str]]:
    errors = []

    # Test base query
    base_query_sql = f"SELECT * FROM ({entity.base_query}) LIMIT 1"
    is_valid, error = self.test_query_execution(base_query_sql)

    # Test all attributes in context
    if base_query_lower.startswith('select'):
        attribute_selects = []
        for attr_key, attr in entity.attributes.items():
            attribute_selects.append(f"({attr.sql}) AS {attr_key}")

        test_sql = f"SELECT {', '.join(attribute_selects)} {from_clause} LIMIT 1"
        is_valid, error = self.test_query_execution(test_sql)

    return len(errors) == 0, errors
```

### Validation Techniques

#### 1. Base Query Testing
- Wraps base query in `SELECT * FROM (...) LIMIT 1`
- Executes against actual database
- Verifies table existence and join syntax

#### 2. Attribute SQL Testing
- Constructs test queries with all attributes
- Tests attributes in their proper context
- Validates SQL expressions and functions

#### 3. Join Logic Validation
```python
def validate_join_logic(self, base_query: str) -> Tuple[bool, Optional[str]]:
    test_sql = f"SELECT COUNT(*) FROM ({base_query})"
    cursor = self.db_inspector.connection.execute(test_sql)
    count = cursor.fetchone()[0]

    # Check for potential Cartesian products
    if count > 100000:
        return False, f"Query returns {count} rows, possible Cartesian product"

    return True, None
```

#### 4. Error Recovery Strategies
- Individual attribute testing on collective failure
- Graceful degradation for complex queries
- Assumption of validity for working base queries

### Performance Optimizations
- `LIMIT 1` queries to minimize execution time
- Connection reuse across validations
- Efficient error propagation

## Layer 3: Semantic Validation

### Purpose
Ensures the generated entities are logically correct and make business sense.

### Implementation
The `SemanticValidator` class (`src/validation.py:200-307`) performs business logic validation:

```python
def validate_business_metrics(self, semantic_layer: SemanticLayerModel) -> List[str]:
    warnings = []

    for entity_key, entity in semantic_layer.entities.items():
        for attr_key, attr in entity.attributes.items():
            warning = self._check_known_metric(entity_key, attr_key, entity, attr)
            if warning:
                warnings.append(warning)

    return warnings
```

### Validation Mechanisms

#### 1. Business Metrics Validation
Compares calculated values against known business metrics:

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

#### 2. Metric Pattern Matching
```python
metric_patterns = {
    "total_amount": "average_order_value",
    "order_value": "average_order_value",
    "average_amount": "average_order_value",
}
```

#### 3. Plausibility Checks
```python
def check_metric_plausibility(self, entity_name: str, attribute_name: str, calculated_value: Any) -> Tuple[bool, Optional[str]]:
    if isinstance(calculated_value, (int, float)):
        if calculated_value < 0 and "amount" in attribute_name.lower():
            return False, f"Negative amount value: {calculated_value}"
        if calculated_value > 1000000:  # Very high values
            return False, f"Suspiciously high value: {calculated_value}"

    return True, None
```

#### 4. Cardinality Validation
```python
def validate_cardinality_expectations(self, entity: EntityModel) -> List[str]:
    warnings = []
    cursor = self.db_inspector.connection.execute(f"SELECT COUNT(*) FROM ({entity.base_query})")
    count = cursor.fetchone()[0]

    if count == 0:
        warnings.append("Entity query returns no results")
    elif count > 10000:  # Much larger than expected for Northwind
        warnings.append(f"Entity query returns unusually high count: {count}")

    return warnings
```

## Validation Orchestration

### Implementation
The `ValidationOrchestrator` class (`src/validation.py:309-472`) coordinates all validation layers:

```python
def validate_semantic_layer(self, semantic_layer_json: Dict[str, Any]) -> Dict[str, Any]:
    # Layer 1: Structural validation
    struct_valid, struct_errors = self.structural_validator.validate_semantic_layer(semantic_layer_json)

    if not struct_valid:
        return {"overall_valid": False, "structural": {"valid": False, "errors": struct_errors}}

    # Layer 2: SQL validation
    semantic_layer = SemanticLayerModel(**semantic_layer_json)
    sql_errors, failed_entities = [], []

    for entity_key, entity in semantic_layer.entities.items():
        entity_valid, entity_errors = self.sql_validator.validate_entity_sql(entity)
        if not entity_valid:
            failed_entities.append(entity_key)
            sql_errors.extend([f"{entity_key}: {error}" for error in entity_errors])

    # Layer 3: Semantic validation
    semantic_warnings = self.semantic_validator.validate_business_metrics(semantic_layer)

    return {
        "overall_valid": len(failed_entities) == 0,
        "structural": {"valid": struct_valid, "errors": struct_errors},
        "sql": {"valid": len(failed_entities) == 0, "errors": sql_errors, "failed_entities": failed_entities},
        "semantic": {"valid": True, "warnings": semantic_warnings},
        "failed_entities": failed_entities,
    }
```

### Validation Flow
1. **Fast-Fail on Structure**: Stops immediately if JSON structure is invalid
2. **Comprehensive SQL Testing**: Tests every entity and attribute
3. **Business Logic Warnings**: Generates warnings without failing validation
4. **Detailed Reporting**: Provides comprehensive validation reports

## Feedback and Repair Mechanisms

### Failed Entity Handling
The pipeline automatically handles validation failures:

```python
def handle_validation_failures(self, semantic_layer: Dict[str, Any], validation_results: Dict[str, Any]) -> Dict[str, Any]:
    failed_entities = self.validator.get_failed_entities(validation_results)

    if not failed_entities:
        return semantic_layer

    entities = semantic_layer.get("entities", {})
    removed_entities = []

    for entity_key in failed_entities:
        if entity_key in entities:
            del entities[entity_key]
            removed_entities.append(entity_key)

    return semantic_layer
```

### Re-validation Process
After removing failed entities, the pipeline re-validates:

```python
if not validation_results["overall_valid"]:
    semantic_layer = self.handle_validation_failures(semantic_layer, validation_results)
    # Re-validate after fixes
    validation_results = self.validate_generated_layer(semantic_layer)
```

## Quality Metrics and Reporting

### Validation Report Generation
```python
def generate_validation_report(self, results: Dict[str, Any]) -> str:
    report = ["=== SEMANTIC LAYER VALIDATION REPORT ===\n"]

    # Overall status
    status = "PASSED" if results["overall_valid"] else "FAILED"
    report.append(f"Overall Status: {status}\n")

    # Layer-by-layer results
    # ... detailed reporting for each layer

    return "\n".join(report)
```

### Success Metrics
The validation system tracks:
- **Pass Rate**: Percentage of entities passing each validation layer
- **Error Distribution**: Types and frequency of validation errors
- **Performance Metrics**: Validation time per layer and entity
- **Business Accuracy**: Alignment with known business metrics

### Validation Output Examples

#### Successful Validation
```
=== SEMANTIC LAYER VALIDATION REPORT ===

Overall Status: PASSED

1. Structural Validation:
   ✓ PASSED - JSON structure is valid

2. SQL Validation:
   ✓ PASSED - All SQL queries are syntactically correct

3. Semantic Validation:
   ✓ PASSED - No semantic issues detected
```

#### Failed Validation with Recovery
```
=== SEMANTIC LAYER VALIDATION REPORT ===

Overall Status: PASSED (after entity removal)

1. Structural Validation:
   ✓ PASSED - JSON structure is valid

2. SQL Validation:
   ⚠ PARTIAL - 5/6 entities passed
     - inventory_management: Base query failed: no such table: StockLevels
   Failed entities: inventory_management

3. Semantic Validation:
   ⚠ WARNINGS - Some metrics may need review
     - Metric 'total_amount' value 1450 differs significantly from expected 1274
```

## Performance Characteristics

### Validation Speed
- **Layer 1**: ~10ms (in-memory validation)
- **Layer 2**: ~100-500ms per entity (database queries)
- **Layer 3**: ~50-200ms per entity (business logic checks)

### Scalability Considerations
- Sequential entity validation for clear error attribution
- Database connection reuse for efficiency
- Configurable timeout for SQL execution
- Memory-efficient error reporting

## Future Enhancements

### Planned Improvements
1. **Parallel Validation**: Concurrent entity validation for large semantic layers
2. **Smart Repair**: LLM-based automatic fixing of failed entities
3. **Custom Validators**: Plugin architecture for domain-specific validation rules
4. **Validation Caching**: Cache validation results for unchanged entities
5. **Advanced Metrics**: Machine learning-based anomaly detection for business metrics

### Experimental Features
1. **Self-Healing Validation**: Automatic query optimization for performance issues
2. **Cross-Entity Validation**: Validation of relationships between entities
3. **Data Quality Checks**: Integration with data profiling tools
4. **Real-time Validation**: Streaming validation for large datasets

This comprehensive validation framework ensures that the generated semantic layers are not only technically correct but also business-ready and aligned with real-world data patterns and business requirements.