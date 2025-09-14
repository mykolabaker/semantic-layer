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
        self.db_inspector.connect()

    def extract_database_metadata(self) -> Dict[str, Any]:
        """Extract and cache database metadata."""
        self.logger.info("Extracting database metadata")

        if not self.schema_context:
            self.schema_context = self.db_inspector.extract_all_metadata()

            # Save schema context for debugging
            Path("output").mkdir(exist_ok=True)
            with open("output/schema_context.json", "w") as f:
                json.dump(self.schema_context, f, indent=2, default=str)

        return self.schema_context or {}

    def identify_business_entities(self) -> List[Dict[str, Any]]:
        """Use LLM to identify core business entities from schema."""
        self.logger.info("Identifying business entities with LLM")

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

        schema_context = self.schema_context or {}
        response = self.llm_service.generate_entity_identification(
            schema_context, business_context
        )

        entities = response.get("entities", [])
        self.logger.info(f"Identified {len(entities)} business entities")

        return entities

    def generate_entity_definitions(
        self, entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate detailed definitions for each identified entity."""
        self.logger.info("Generating detailed entity definitions")

        semantic_layer: Dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "database": "northwind.db",
            "entities": {},
        }

        for entity in entities:
            entity_name = entity["name"]
            self.logger.info(f"Generating definition for entity: {entity_name}")

            try:
                schema_context = self.schema_context or {}
                entity_details = self.llm_service.generate_entity_details(
                    entity_name, entity, schema_context
                )
                semantic_layer["entities"][entity_name] = entity_details
            except Exception as e:
                self.logger.error(f"Failed to generate entity {entity_name}: {e}")
                continue

        return semantic_layer

    def validate_generated_layer(
        self, semantic_layer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run validation suite on generated semantic layer."""
        self.logger.info("Validating generated semantic layer")

        validation_results = self.validator.validate_semantic_layer(semantic_layer)

        # Generate and log validation report
        report = self.validator.generate_validation_report(validation_results)
        self.logger.info(f"Validation report:\n{report}")

        # Save validation report
        Path("output").mkdir(exist_ok=True)
        with open("output/validation_report.txt", "w") as f:
            f.write(report)

        return validation_results

    def handle_validation_failures(
        self, semantic_layer: Dict[str, Any], validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attempt to fix entities that failed validation."""
        failed_entities = self.validator.get_failed_entities(validation_results)

        if not failed_entities:
            return semantic_layer

        self.logger.info(f"Attempting to fix {len(failed_entities)} failed entities")

        # For now, remove failed entities (could implement LLM-based repair)
        entities = semantic_layer.get("entities", {})
        for entity_key in failed_entities:
            if entity_key in entities:
                self.logger.warning(f"Removing failed entity: {entity_key}")
                del entities[entity_key]

        return semantic_layer

    def save_semantic_layer(
        self, semantic_layer: Dict[str, Any], output_path: str
    ) -> None:
        """Save final semantic layer to JSON file."""
        self.logger.info(f"Saving semantic layer to {output_path}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(semantic_layer, f, indent=2, default=str)

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
        self.logger.info("Starting semantic layer generation pipeline")

        try:
            # Step 1: Initialize components
            self.initialize_components()

            # Step 2: Extract database metadata
            self.extract_database_metadata()

            # Step 3: Identify business entities
            entities = self.identify_business_entities()

            # Step 4: Generate entity definitions
            semantic_layer = self.generate_entity_definitions(entities)

            # Step 5: Validate generated layer
            validation_results = self.validate_generated_layer(semantic_layer)

            # Step 6: Handle validation failures
            if not validation_results["overall_valid"]:
                semantic_layer = self.handle_validation_failures(
                    semantic_layer, validation_results
                )
                # Re-validate after fixes
                validation_results = self.validate_generated_layer(semantic_layer)

            # Step 7: Save final semantic layer
            self.save_semantic_layer(semantic_layer, output_path)

            # Generate execution results
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            results = {
                "success": True,
                "execution_time": execution_time,
                "entity_count": len(semantic_layer.get("entities", {})),
                "valid_entity_count": len(semantic_layer.get("entities", {})),
                "entity_names": list(semantic_layer.get("entities", {}).keys()),
                "validation_passed": validation_results["overall_valid"],
                "warnings": validation_results.get("semantic", {}).get("warnings", []),
                "output_path": output_path,
            }

            # Generate and save pipeline report
            report = self.generate_pipeline_report(results)
            self.logger.info(f"Pipeline report:\n{report}")

            with open("output/pipeline_report.txt", "w") as f:
                f.write(report)

            return results

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {e}")
            raise
        finally:
            # Cleanup
            if self.db_inspector:
                self.db_inspector.disconnect()
