"""
Main pipeline orchestrator that coordinates all components
in the semantic layer generation process.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from src.db_inspector import DatabaseInspector
from src.llm_service import LLMService
from src.validation import ValidationOrchestrator
from src.config import Config


class PipelineOrchestrator:
    """Main orchestrator for the semantic layer generation pipeline."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.db_inspector = DatabaseInspector(config.database_config.connection_string)
        self.llm_service = LLMService(config.llm_config)
        self.validator = ValidationOrchestrator(
            self.db_inspector, config.business_metrics
        )

        self.schema_context: Optional[Dict[str, Any]] = None

    def initialize_components(self) -> None:
        """Initialize all pipeline components."""
        self.logger.info("Initializing pipeline components")
        self.logger.debug(f"Database connection string: {self.config.database_config.connection_string}")
        self.logger.debug(f"LLM provider: {self.config.llm_config.provider}")
        self.logger.debug(f"LLM model: {self.config.llm_config.model}")
        self.logger.debug(f"LLM cache enabled: {self.config.llm_config.cache_enabled}")

        self.logger.info("Connecting to database...")
        self.db_inspector.connect()
        self.logger.info("Database connection established successfully")

        self.logger.info("LLM service initialized")
        self.logger.info("Validation orchestrator initialized")
        self.logger.info("All pipeline components initialized successfully")

    def extract_database_metadata(self) -> Dict[str, Any]:
        """Extract and cache database metadata."""
        self.logger.info("Extracting database metadata")

        if not self.schema_context:
            self.logger.info("Schema context not cached, extracting from database...")
            start_time = datetime.now()
            self.schema_context = self.db_inspector.extract_all_metadata()
            extraction_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(f"Database metadata extraction completed in {extraction_time:.2f} seconds")
            self.logger.info(f"Found {self.schema_context.get('table_count', 0)} tables")

            table_names = list(self.schema_context.get('tables', {}).keys())
            self.logger.debug(f"Table names: {table_names}")

            total_rows = sum(table.get('row_count', 0) for table in self.schema_context.get('tables', {}).values())
            self.logger.info(f"Total rows across all tables: {total_rows}")

            # Save schema context for debugging
            Path("output").mkdir(exist_ok=True)
            schema_file = "output/schema_context.json"
            with open(schema_file, "w") as f:
                json.dump(self.schema_context, f, indent=2, default=str)
            self.logger.debug(f"Schema context saved to {schema_file}")
        else:
            self.logger.info("Using cached schema context")

        return self.schema_context or {}

    def identify_business_entities(self) -> List[Dict[str, Any]]:
        """Use LLM to identify core business entities from schema."""
        self.logger.info("Identifying business entities with LLM")
        start_time = datetime.now()

        # Load business context from documentation
        business_context = """
        Northwind Traders is a specialty foods wholesale distributor with these core functions:
        1. Product Sourcing & Supply Chain - 29 suppliers, 77 products in 8 categories
        2. Sales & Customer Management - 91 customers, 9 sales representatives, ~830 orders
        3. Logistics & Distribution - 3 shipping companies, international operations

        Key business metrics:
        - Average Order Value: $1,274
        - Average Items per Order: 2.6
        - Customer Retention Rate: 89%
        - Average Fulfillment Time: 8 days
        """

        self.logger.debug("Preparing LLM prompt for entity identification")
        schema_context = self.schema_context or {}
        self.logger.debug(f"Schema context contains {len(schema_context.get('tables', {}))} tables")

        self.logger.info("Sending entity identification request to LLM...")
        response = self.llm_service.generate_entity_identification(
            schema_context, business_context
        )

        identification_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Entity identification completed in {identification_time:.2f} seconds")

        entities = response.get("entities", [])
        self.logger.info(f"Successfully identified {len(entities)} business entities")

        for i, entity in enumerate(entities, 1):
            entity_name = entity.get('name', 'Unknown')
            entity_tables = entity.get('primary_tables', [])
            self.logger.debug(f"Entity {i}: {entity_name} (tables: {entity_tables})")

        return entities

    def generate_entity_definitions(
        self, entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate detailed definitions for each identified entity."""
        self.logger.info(f"Generating detailed entity definitions for {len(entities)} entities")
        start_time = datetime.now()

        semantic_layer: Dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "database": "northwind.db",
            "entities": {},
        }

        successful_entities = 0
        failed_entities = 0

        for i, entity in enumerate(entities, 1):
            entity_name = entity["name"]
            entity_description = entity.get("description", "")
            primary_tables = entity.get("primary_tables", [])

            self.logger.info(f"[{i}/{len(entities)}] Generating definition for entity: {entity_name}")
            self.logger.debug(f"Entity description: {entity_description}")
            self.logger.debug(f"Primary tables: {primary_tables}")

            entity_start_time = datetime.now()

            try:
                schema_context = self.schema_context or {}
                self.logger.debug(f"Sending entity details request to LLM for: {entity_name}")

                entity_details = self.llm_service.generate_entity_details(
                    entity_name, entity, schema_context
                )

                entity_time = (datetime.now() - entity_start_time).total_seconds()
                self.logger.info(f"Entity {entity_name} definition generated in {entity_time:.2f} seconds")

                # Log some details about the generated entity
                if isinstance(entity_details, dict):
                    attrs_count = len(entity_details.get('attributes', {}))
                    relations_count = len(entity_details.get('relations', {}))
                    self.logger.debug(f"Generated {attrs_count} attributes and {relations_count} relations for {entity_name}")

                semantic_layer["entities"][entity_name] = entity_details
                successful_entities += 1

            except Exception as e:
                entity_time = (datetime.now() - entity_start_time).total_seconds()
                self.logger.error(f"Failed to generate entity {entity_name} after {entity_time:.2f} seconds: {e}")
                failed_entities += 1
                continue

        total_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Entity definition generation completed in {total_time:.2f} seconds")
        self.logger.info(f"Successfully generated: {successful_entities} entities")
        if failed_entities > 0:
            self.logger.warning(f"Failed to generate: {failed_entities} entities")

        return semantic_layer

    def validate_generated_layer(
        self, semantic_layer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run validation suite on generated semantic layer."""
        entity_count = len(semantic_layer.get("entities", {}))
        self.logger.info(f"Validating generated semantic layer with {entity_count} entities")
        start_time = datetime.now()

        self.logger.debug("Starting structural validation...")
        validation_results = self.validator.validate_semantic_layer(semantic_layer)
        validation_time = (datetime.now() - start_time).total_seconds()

        self.logger.info(f"Validation completed in {validation_time:.2f} seconds")

        # Log validation summary
        overall_valid = validation_results.get("overall_valid", False)
        structural_valid = validation_results.get("structural", {}).get("valid", False)
        sql_valid = validation_results.get("sql", {}).get("valid", False)
        failed_entities = validation_results.get("failed_entities", [])

        self.logger.info(f"Validation results: Overall={overall_valid}, Structural={structural_valid}, SQL={sql_valid}")
        if failed_entities:
            self.logger.warning(f"Failed entities: {failed_entities}")

        sql_errors = validation_results.get("sql", {}).get("errors", [])
        if sql_errors:
            self.logger.error(f"SQL validation errors ({len(sql_errors)} total):")
            for error in sql_errors[:5]:  # Log first 5 errors
                self.logger.error(f"  - {error}")
            if len(sql_errors) > 5:
                self.logger.error(f"  ... and {len(sql_errors) - 5} more errors")

        semantic_warnings = validation_results.get("semantic", {}).get("warnings", [])
        if semantic_warnings:
            self.logger.warning(f"Semantic validation warnings ({len(semantic_warnings)} total):")
            for warning in semantic_warnings:
                self.logger.warning(f"  - {warning}")

        # Generate and log validation report
        report = self.validator.generate_validation_report(validation_results)
        self.logger.debug(f"Full validation report:\n{report}")

        # Save validation report
        Path("output").mkdir(exist_ok=True)
        report_file = "output/validation_report.txt"
        with open(report_file, "w") as f:
            f.write(report)
        self.logger.debug(f"Validation report saved to {report_file}")

        return validation_results

    def handle_validation_failures(
        self, semantic_layer: Dict[str, Any], validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to fix entities that failed validation."""
        failed_entities = self.validator.get_failed_entities(validation_results)

        if not failed_entities:
            self.logger.info("No failed entities to handle")
            return semantic_layer

        self.logger.warning(f"Handling {len(failed_entities)} failed entities: {failed_entities}")
        start_time = datetime.now()

        # For now, remove failed entities (could implement LLM-based repair)
        entities = semantic_layer.get("entities", {})
        removed_entities = []

        for entity_key in failed_entities:
            if entity_key in entities:
                self.logger.warning(f"Removing failed entity: {entity_key}")
                del entities[entity_key]
                removed_entities.append(entity_key)
            else:
                self.logger.warning(f"Failed entity {entity_key} not found in semantic layer")

        handling_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Validation failure handling completed in {handling_time:.2f} seconds")
        self.logger.info(f"Removed {len(removed_entities)} failed entities: {removed_entities}")
        self.logger.info(f"Remaining entities: {len(entities)}")

        return semantic_layer

    def save_semantic_layer(
        self, semantic_layer: Dict[str, Any], output_path: str
    ) -> None:
        """Save final semantic layer to JSON file."""
        entity_count = len(semantic_layer.get("entities", {}))
        self.logger.info(f"Saving semantic layer with {entity_count} entities to {output_path}")
        start_time = datetime.now()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Created output directory: {Path(output_path).parent}")

        with open(output_path, "w") as f:
            json.dump(semantic_layer, f, indent=2, default=str)

        file_size = Path(output_path).stat().st_size
        save_time = (datetime.now() - start_time).total_seconds()

        self.logger.info(f"Semantic layer saved successfully in {save_time:.2f} seconds")
        self.logger.debug(f"Output file size: {file_size} bytes")

        # Log summary of what was saved
        for entity_name in semantic_layer.get("entities", {}).keys():
            self.logger.debug(f"Saved entity: {entity_name}")

    def generate_pipeline_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive report of pipeline execution."""
        report = [
            "=== SEMANTIC LAYER PIPELINE EXECUTION REPORT ===",
            f"Execution Time: {results.get('execution_time', 'N/A')} seconds",
            f"Total Entities Generated: {results.get('entity_count', 0)}",
            f"Entities Passed Validation: {results.get('valid_entity_count', 0)}",
            f"Validation Status: {'PASSED' if results.get('validation_passed', False) else 'FAILED'}",
            "",
            "Generated Entities:",
        ]

        for entity_name in results.get("entity_names", []):
            report.append(f"  - {entity_name}")

        if results.get("warnings"):
            report.append("\nWarnings:")
            for warning in results["warnings"]:
                report.append(f"  - {warning}")

        return "\n".join(report)

    def run_pipeline(
        self, output_path: str = "output/semantic_layer.json"
    ) -> Dict[str, Any]:
        """Execute complete pipeline from start to finish."""
        start_time = datetime.now()
        self.logger.info("=== STARTING SEMANTIC LAYER GENERATION PIPELINE ===")
        self.logger.info(f"Pipeline start time: {start_time.isoformat()}")
        self.logger.info(f"Target output path: {output_path}")

        try:
            # Step 1: Initialize components
            self.logger.info("STEP 1: Initializing pipeline components")
            step_start = datetime.now()
            self.initialize_components()
            step_time = (datetime.now() - step_start).total_seconds()
            self.logger.info(f"STEP 1 completed in {step_time:.2f} seconds")

            # Step 2: Extract database metadata
            self.logger.info("STEP 2: Extracting database metadata")
            step_start = datetime.now()
            self.extract_database_metadata()
            step_time = (datetime.now() - step_start).total_seconds()
            self.logger.info(f"STEP 2 completed in {step_time:.2f} seconds")

            # Step 3: Identify business entities
            self.logger.info("STEP 3: Identifying business entities")
            step_start = datetime.now()
            entities = self.identify_business_entities()
            step_time = (datetime.now() - step_start).total_seconds()
            self.logger.info(f"STEP 3 completed in {step_time:.2f} seconds")

            # Step 4: Generate entity definitions
            self.logger.info("STEP 4: Generating entity definitions")
            step_start = datetime.now()
            semantic_layer = self.generate_entity_definitions(entities)
            step_time = (datetime.now() - step_start).total_seconds()
            self.logger.info(f"STEP 4 completed in {step_time:.2f} seconds")

            # Step 5: Validate generated layer
            self.logger.info("STEP 5: Validating generated semantic layer")
            step_start = datetime.now()
            validation_results = self.validate_generated_layer(semantic_layer)
            step_time = (datetime.now() - step_start).total_seconds()
            self.logger.info(f"STEP 5 completed in {step_time:.2f} seconds")

            # Step 6: Handle validation failures
            if not validation_results["overall_valid"]:
                self.logger.info("STEP 6: Handling validation failures")
                step_start = datetime.now()
                semantic_layer = self.handle_validation_failures(
                    semantic_layer, validation_results
                )

                # Re-validate after fixes
                self.logger.info("STEP 6a: Re-validating after fixes")
                validation_results = self.validate_generated_layer(semantic_layer)
                step_time = (datetime.now() - step_start).total_seconds()
                self.logger.info(f"STEP 6 completed in {step_time:.2f} seconds")
            else:
                self.logger.info("STEP 6: Skipped - no validation failures to handle")

            # Step 7: Save final semantic layer
            self.logger.info("STEP 7: Saving final semantic layer")
            step_start = datetime.now()
            self.save_semantic_layer(semantic_layer, output_path)
            step_time = (datetime.now() - step_start).total_seconds()
            self.logger.info(f"STEP 7 completed in {step_time:.2f} seconds")

            # Generate execution results
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            final_entity_count = len(semantic_layer.get("entities", {}))
            entity_names = list(semantic_layer.get("entities", {}).keys())
            validation_passed = validation_results["overall_valid"]
            warnings = validation_results.get("semantic", {}).get("warnings", [])

            results = {
                "success": True,
                "execution_time": execution_time,
                "entity_count": final_entity_count,
                "valid_entity_count": final_entity_count,
                "entity_names": entity_names,
                "validation_passed": validation_passed,
                "warnings": warnings,
                "output_path": output_path,
            }

            self.logger.info("=== PIPELINE EXECUTION SUMMARY ===")
            self.logger.info(f"Total execution time: {execution_time:.2f} seconds")
            self.logger.info(f"Final entity count: {final_entity_count}")
            self.logger.info(f"Validation passed: {validation_passed}")
            self.logger.info(f"Warning count: {len(warnings)}")
            self.logger.info(f"Generated entities: {entity_names}")

            # Generate and save pipeline report
            report = self.generate_pipeline_report(results)
            self.logger.debug(f"Full pipeline report:\n{report}")

            report_file = "output/pipeline_report.txt"
            with open(report_file, "w") as f:
                f.write(report)
            self.logger.info(f"Pipeline report saved to {report_file}")

            self.logger.info("=== PIPELINE COMPLETED SUCCESSFULLY ===")
            return results

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"=== PIPELINE EXECUTION FAILED ===")
            self.logger.error(f"Error occurred after {execution_time:.2f} seconds")
            self.logger.error(f"Error details: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            raise
        finally:
            # Cleanup
            self.logger.info("Performing cleanup operations...")
            if self.db_inspector:
                self.db_inspector.disconnect()
                self.logger.info("Database connection closed")
            cleanup_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Pipeline cleanup completed after {cleanup_time:.2f} seconds total")
