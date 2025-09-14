"""
Main entry point for the semantic layer pipeline.
Handles command-line arguments and pipeline execution.
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from src.config import Config
from src.orchestrator import PipelineOrchestrator


def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            ),
        ],
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate semantic layer from Northwind database"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="output/semantic_layer.json",
        help="Output file path (default: output/semantic_layer.json)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable LLM response caching"
    )
    return parser.parse_args()


def main() -> None:
    """Main execution function."""
    args = parse_arguments()
    setup_logging(args.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting Semantic Layer Pipeline")

    try:
        # Initialize configuration
        config = Config()
        if args.no_cache:
            config.llm_config.cache_enabled = False

        # Create output directory
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Run pipeline
        orchestrator = PipelineOrchestrator(config)
        results = orchestrator.run_pipeline(str(output_path))

        # Report results
        logger.info("Pipeline completed successfully")
        logger.info(f"Generated entities: {results['entity_count']}")
        logger.info(f"Validation passed: {results['validation_passed']}")
        logger.info(f"Output saved to: {args.output}")

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
