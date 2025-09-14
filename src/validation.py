"""
Multi-layered validation system for ensuring structural correctness,
SQL syntax validity, and semantic accuracy of the generated semantic layer.
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from src.models import SemanticLayerModel, EntityModel, AttributeModel
from src.db_inspector import DatabaseInspector


class StructuralValidator:
    """Validates JSON structure using Pydantic models."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_semantic_layer(
        self, semantic_layer_json: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate complete semantic layer structure."""
        errors = []

        try:
            SemanticLayerModel(**semantic_layer_json)
            self.logger.info("Structural validation passed")
            return True, []
        except Exception as e:
            errors.append(f"Structural validation failed: {str(e)}")
            self.logger.error(f"Structural validation failed: {e}")
            return False, errors


class SQLValidator:
    """Validates SQL syntax by executing test queries against database."""

    def __init__(self, db_inspector: DatabaseInspector):
        self.db_inspector = db_inspector
        self.logger = logging.getLogger(__name__)

    def validate_entity_sql(self, entity: EntityModel) -> Tuple[bool, List[str]]:
        """Validate SQL syntax for an entity's base query and attributes."""
        errors = []

        # Test base query
        is_valid, error = self.test_query_execution(
            f"SELECT * FROM ({entity.base_query}) LIMIT 1"
        )
        if not is_valid:
            errors.append(f"Base query failed: {error}")

        # Test each attribute
        for attr_key, attr in entity.attributes.items():
            test_sql = f"SELECT {attr.sql} FROM ({entity.base_query}) LIMIT 1"
            is_valid, error = self.test_query_execution(test_sql)
            if not is_valid:
                errors.append(f"Attribute '{attr_key}' failed: {error}")

        return len(errors) == 0, errors

    def test_query_execution(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        """Test if a SQL query can be executed successfully."""
        try:
            if not self.db_inspector.connection:
                self.db_inspector.connect()
            if self.db_inspector.connection is None:
                raise RuntimeError("Database connection not established")
            cursor = self.db_inspector.connection.execute(sql_query)
            cursor.fetchall()  # Consume results
            return True, None
        except Exception as e:
            return False, str(e)

    def validate_join_logic(self, base_query: str) -> Tuple[bool, Optional[str]]:
        """Check for potential Cartesian products and join issues."""
        try:
            # Execute query and check if result count seems reasonable
            test_sql = f"SELECT COUNT(*) FROM ({base_query})"
            if not self.db_inspector.connection:
                self.db_inspector.connect()
            if self.db_inspector.connection is None:
                raise RuntimeError("Database connection not established")
            cursor = self.db_inspector.connection.execute(test_sql)
            count = cursor.fetchone()[0]

            # Heuristic: if result count is suspiciously high, might be Cartesian product
            if count > 100000:  # Threshold for potential issues
                return False, f"Query returns {count} rows, possible Cartesian product"

            return True, None
        except Exception as e:
            return False, f"Join validation failed: {str(e)}"


class SemanticValidator:
    """Validates semantic accuracy using business logic checks."""

    def __init__(
        self, db_inspector: DatabaseInspector, business_metrics: Dict[str, Any]
    ):
        self.db_inspector = db_inspector
        self.business_metrics = business_metrics
        self.logger = logging.getLogger(__name__)

    def validate_business_metrics(
        self, semantic_layer: SemanticLayerModel
    ) -> List[str]:
        """Compare calculated metrics against known business values."""
        warnings = []

        # Check specific business metrics if they exist in entities
        for entity_key, entity in semantic_layer.entities.items():
            for attr_key, attr in entity.attributes.items():
                warning = self._check_known_metric(entity_key, attr_key, entity, attr)
                if warning:
                    warnings.append(warning)

        return warnings

    def _check_known_metric(
        self, entity_key: str, attr_key: str, entity: EntityModel, attr: AttributeModel
    ) -> Optional[str]:
        """Check if an attribute matches a known business metric."""
        # Map common attribute patterns to business metrics
        metric_patterns = {
            "total_amount": "average_order_value",
            "order_value": "average_order_value",
            "average_amount": "average_order_value",
        }

        if attr_key.lower() in metric_patterns:
            metric_key = metric_patterns[attr_key.lower()]
            if metric_key in self.business_metrics:
                calculated_value = self._calculate_metric_value(entity, attr)
                expected_value = self.business_metrics[metric_key]

                if (
                    calculated_value
                    and abs(calculated_value - expected_value) / expected_value > 0.1
                ):
                    return f"Metric '{attr_key}' value {calculated_value} differs significantly from expected {expected_value}"

        return None

    def _calculate_metric_value(
        self, entity: EntityModel, attr: AttributeModel
    ) -> Optional[float]:
        """Calculate the actual value of a metric from the database."""
        try:
            if not self.db_inspector.connection:
                self.db_inspector.connect()

            # Simple calculation - could be enhanced
            test_sql = f"SELECT AVG({attr.sql}) FROM ({entity.base_query})"
            if self.db_inspector.connection is None:
                raise RuntimeError("Database connection not established")
            cursor = self.db_inspector.connection.execute(test_sql)
            result = cursor.fetchone()[0]
            return float(result) if result else None
        except Exception:
            return None

    def check_metric_plausibility(
        self, entity_name: str, attribute_name: str, calculated_value: Any
    ) -> Tuple[bool, Optional[str]]:
        """Check if calculated metric value is plausible."""
        # Basic plausibility checks
        if isinstance(calculated_value, (int, float)):
            if calculated_value < 0 and "amount" in attribute_name.lower():
                return False, f"Negative amount value: {calculated_value}"
            if calculated_value > 1000000:  # Very high values
                return False, f"Suspiciously high value: {calculated_value}"

        return True, None

    def validate_cardinality_expectations(self, entity: EntityModel) -> List[str]:
        """Validate that entity queries don't produce unexpected result counts."""
        warnings = []

        try:
            if not self.db_inspector.connection:
                self.db_inspector.connect()

            # Check total count
            if self.db_inspector.connection is None:
                raise RuntimeError("Database connection not established")
            cursor = self.db_inspector.connection.execute(
                f"SELECT COUNT(*) FROM ({entity.base_query})"
            )
            count = cursor.fetchone()[0]

            # Heuristic checks based on known data size
            if count == 0:
                warnings.append("Entity query returns no results")
            elif count > 10000:  # Much larger than expected for Northwind
                warnings.append(f"Entity query returns unusually high count: {count}")

        except Exception as e:
            warnings.append(f"Could not validate cardinality: {str(e)}")

        return warnings


class ValidationOrchestrator:
    """Orchestrates all validation layers and manages feedback loops."""

    def __init__(
        self, db_inspector: DatabaseInspector, business_metrics: Dict[str, Any]
    ):
        self.structural_validator = StructuralValidator()
        self.sql_validator = SQLValidator(db_inspector)
        self.semantic_validator = SemanticValidator(db_inspector, business_metrics)
        self.logger = logging.getLogger(__name__)

    def validate_semantic_layer(
        self, semantic_layer_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run complete validation suite on semantic layer."""
        self.logger.info("Starting validation suite")

        results = {
            "overall_valid": True,
            "structural": {"valid": False, "errors": []},
            "sql": {"valid": False, "errors": [], "failed_entities": []},
            "semantic": {"valid": True, "warnings": []},
            "failed_entities": [],
        }

        # Layer 1: Structural validation
        struct_valid, struct_errors = self.structural_validator.validate_semantic_layer(
            semantic_layer_json
        )
        results["structural"] = {"valid": struct_valid, "errors": struct_errors}

        if not struct_valid:
            results["overall_valid"] = False
            return results

        # Parse validated structure
        semantic_layer = SemanticLayerModel(**semantic_layer_json)

        # Layer 2: SQL validation
        sql_errors = []
        failed_entities = []

        for entity_key, entity in semantic_layer.entities.items():
            entity_valid, entity_errors = self.sql_validator.validate_entity_sql(entity)
            if not entity_valid:
                failed_entities.append(entity_key)
                sql_errors.extend([f"{entity_key}: {error}" for error in entity_errors])

        results["sql"] = {
            "valid": len(failed_entities) == 0,
            "errors": sql_errors,
            "failed_entities": failed_entities,
        }

        if failed_entities:
            results["overall_valid"] = False
            results["failed_entities"] = failed_entities

        # Layer 3: Semantic validation (warnings only)
        semantic_warnings = self.semantic_validator.validate_business_metrics(
            semantic_layer
        )
        results["semantic"] = {"valid": True, "warnings": semantic_warnings}

        self.logger.info(
            f"Validation completed. Overall valid: {results['overall_valid']}"
        )
        return results

    def generate_validation_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable validation report."""
        report = ["=== SEMANTIC LAYER VALIDATION REPORT ===\n"]

        # Overall status
        status = "PASSED" if results["overall_valid"] else "FAILED"
        report.append(f"Overall Status: {status}\n")

        # Structural validation
        report.append("1. Structural Validation:")
        if results["structural"]["valid"]:
            report.append("   ✓ PASSED - JSON structure is valid")
        else:
            report.append("   ✗ FAILED")
            for error in results["structural"]["errors"]:
                report.append(f"     - {error}")
        report.append("")

        # SQL validation
        report.append("2. SQL Validation:")
        if results["sql"]["valid"]:
            report.append("   ✓ PASSED - All SQL queries are syntactically correct")
        else:
            report.append("   ✗ FAILED")
            for error in results["sql"]["errors"]:
                report.append(f"     - {error}")
            report.append(
                f"   Failed entities: {', '.join(results['sql']['failed_entities'])}"
            )
        report.append("")

        # Semantic validation
        report.append("3. Semantic Validation:")
        if not results["semantic"]["warnings"]:
            report.append("   ✓ PASSED - No semantic issues detected")
        else:
            report.append("   ⚠ WARNINGS - Some metrics may need review")
            for warning in results["semantic"]["warnings"]:
                report.append(f"     - {warning}")

        return "\n".join(report)

    def get_failed_entities(self, validation_results: Dict[str, Any]) -> List[str]:
        """Extract list of entities that failed validation for reprocessing."""
        return validation_results.get("failed_entities", [])
