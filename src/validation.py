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
        self.logger.info("Starting structural validation")
        self.logger.debug(f"Validating semantic layer with {len(semantic_layer_json.get('entities', {}))} entities")
        errors = []

        try:
            # Log structure overview
            entities = semantic_layer_json.get('entities', {})
            self.logger.debug(f"Entity names: {list(entities.keys())}")

            # Validate using Pydantic model
            semantic_layer_model = SemanticLayerModel(**semantic_layer_json)

            self.logger.info("Structural validation passed successfully")
            self.logger.debug(f"Validated {len(semantic_layer_model.entities)} entities")
            return True, []
        except Exception as e:
            error_msg = f"Structural validation failed: {str(e)}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            self.logger.error(f"Error type: {type(e).__name__}")

            # Try to provide more specific error information
            if hasattr(e, 'errors'):
                validation_errors = e.errors()
                self.logger.error(f"Pydantic validation errors ({len(validation_errors)} total):")
                for i, error in enumerate(validation_errors[:5]):
                    self.logger.error(f"  {i+1}. {error}")
                if len(validation_errors) > 5:
                    self.logger.error(f"  ... and {len(validation_errors) - 5} more errors")

            return False, errors


class SQLValidator:
    """Validates SQL syntax by executing test queries against database."""

    def __init__(self, db_inspector: DatabaseInspector):
        self.db_inspector = db_inspector
        self.logger = logging.getLogger(__name__)

    def validate_entity_sql(self, entity: EntityModel) -> Tuple[bool, List[str]]:
        """Validate SQL syntax for an entity's base query and attributes."""
        entity_name = getattr(entity, 'name', 'Unknown')
        self.logger.debug(f"Starting SQL validation for entity: {entity_name}")

        errors = []
        attr_count = len(entity.attributes)
        self.logger.debug(f"Entity has {attr_count} attributes to validate")

        # Test base query
        self.logger.debug(f"Testing base query for entity: {entity_name}")
        base_query_sql = f"SELECT * FROM ({entity.base_query}) LIMIT 1"
        self.logger.debug(f"Base query SQL: {base_query_sql[:100]}...")

        is_valid, error = self.test_query_execution(base_query_sql)
        if not is_valid:
            error_msg = f"Base query failed: {error}"
            errors.append(error_msg)
            self.logger.error(f"Entity {entity_name} - {error_msg}")
        else:
            self.logger.debug(f"Base query validation passed for entity: {entity_name}")

        # Test each attribute
        successful_attrs = 0
        for i, (attr_key, attr) in enumerate(entity.attributes.items(), 1):
            self.logger.debug(f"[{i}/{attr_count}] Testing attribute: {attr_key}")

            test_sql = f"SELECT {attr.sql} FROM ({entity.base_query}) LIMIT 1"
            self.logger.debug(f"Attribute SQL: {attr.sql}")

            is_valid, error = self.test_query_execution(test_sql)
            if not is_valid:
                error_msg = f"Attribute '{attr_key}' failed: {error}"
                errors.append(error_msg)
                self.logger.error(f"Entity {entity_name} - {error_msg}")
            else:
                successful_attrs += 1

        self.logger.info(f"Entity {entity_name} SQL validation: {successful_attrs}/{attr_count} attributes passed")
        if errors:
            self.logger.warning(f"Entity {entity_name} has {len(errors)} SQL validation errors")

        return len(errors) == 0, errors

    def test_query_execution(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        """Test if a SQL query can be executed successfully."""
        try:
            if not self.db_inspector.connection:
                self.logger.debug("No database connection, establishing new connection")
                self.db_inspector.connect()
            if self.db_inspector.connection is None:
                raise RuntimeError("Database connection not established")

            # Execute query with timeout if possible
            cursor = self.db_inspector.connection.execute(sql_query)
            results = cursor.fetchall()

            result_count = len(results)
            self.logger.debug(f"Query executed successfully, returned {result_count} rows")

            return True, None
        except Exception as e:
            error_msg = str(e)
            self.logger.debug(f"Query execution failed: {error_msg}")
            self.logger.debug(f"Failed SQL: {sql_query[:200]}...")
            return False, error_msg

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
        from datetime import datetime
        start_time = datetime.now()

        entity_count = len(semantic_layer_json.get('entities', {}))
        self.logger.info(f"Starting comprehensive validation suite for {entity_count} entities")

        results = {
            "overall_valid": True,
            "structural": {"valid": False, "errors": []},
            "sql": {"valid": False, "errors": [], "failed_entities": []},
            "semantic": {"valid": True, "warnings": []},
            "failed_entities": [],
            "validation_duration_seconds": 0,
        }

        # Layer 1: Structural validation
        self.logger.info("VALIDATION LAYER 1: Structural validation")
        layer1_start = datetime.now()

        struct_valid, struct_errors = self.structural_validator.validate_semantic_layer(
            semantic_layer_json
        )
        results["structural"] = {"valid": struct_valid, "errors": struct_errors}

        layer1_time = (datetime.now() - layer1_start).total_seconds()
        self.logger.info(f"Layer 1 completed in {layer1_time:.2f} seconds - Result: {'PASS' if struct_valid else 'FAIL'}")

        if not struct_valid:
            results["overall_valid"] = False
            results["validation_duration_seconds"] = (datetime.now() - start_time).total_seconds()
            self.logger.warning("Validation stopped due to structural failures")
            return results

        # Parse validated structure
        semantic_layer = SemanticLayerModel(**semantic_layer_json)
        self.logger.debug("Semantic layer model parsed successfully")

        # Layer 2: SQL validation
        self.logger.info("VALIDATION LAYER 2: SQL syntax validation")
        layer2_start = datetime.now()

        sql_errors = []
        failed_entities = []
        successful_entities = 0

        for i, (entity_key, entity) in enumerate(semantic_layer.entities.items(), 1):
            self.logger.debug(f"[{i}/{entity_count}] Validating SQL for entity: {entity_key}")

            entity_valid, entity_errors = self.sql_validator.validate_entity_sql(entity)
            if not entity_valid:
                failed_entities.append(entity_key)
                sql_errors.extend([f"{entity_key}: {error}" for error in entity_errors])
                self.logger.warning(f"Entity {entity_key} failed SQL validation with {len(entity_errors)} errors")
            else:
                successful_entities += 1
                self.logger.debug(f"Entity {entity_key} passed SQL validation")

        results["sql"] = {
            "valid": len(failed_entities) == 0,
            "errors": sql_errors,
            "failed_entities": failed_entities,
        }

        layer2_time = (datetime.now() - layer2_start).total_seconds()
        self.logger.info(f"Layer 2 completed in {layer2_time:.2f} seconds - {successful_entities}/{entity_count} entities passed")

        if failed_entities:
            results["overall_valid"] = False
            results["failed_entities"] = failed_entities
            self.logger.warning(f"SQL validation failed for entities: {failed_entities}")
        else:
            self.logger.info("All entities passed SQL validation")

        # Layer 3: Semantic validation (warnings only)
        self.logger.info("VALIDATION LAYER 3: Semantic/business logic validation")
        layer3_start = datetime.now()

        semantic_warnings = self.semantic_validator.validate_business_metrics(
            semantic_layer
        )
        results["semantic"] = {"valid": True, "warnings": semantic_warnings}

        layer3_time = (datetime.now() - layer3_start).total_seconds()
        warning_count = len(semantic_warnings)
        self.logger.info(f"Layer 3 completed in {layer3_time:.2f} seconds - {warning_count} warnings found")

        if semantic_warnings:
            self.logger.info(f"Semantic validation warnings: {semantic_warnings}")
        else:
            self.logger.info("No semantic validation warnings")

        # Final summary
        total_time = (datetime.now() - start_time).total_seconds()
        results["validation_duration_seconds"] = total_time

        overall_status = "PASSED" if results["overall_valid"] else "FAILED"
        self.logger.info(f"=== VALIDATION SUITE COMPLETED ====")
        self.logger.info(f"Overall result: {overall_status}")
        self.logger.info(f"Total validation time: {total_time:.2f} seconds")
        self.logger.info(f"Structural: {'PASS' if struct_valid else 'FAIL'}, SQL: {successful_entities}/{entity_count} passed, Semantic: {warning_count} warnings")

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
