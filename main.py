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


def setup_logging(log_level: str = "DEBUG") -> None:
    """Configure logging for the application."""
    log_filename = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Create a more detailed format for file logging vs console
    console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with simpler format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = logging.Formatter(console_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with detailed format
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)  # Always debug level for file
    file_formatter = logging.Formatter(file_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Log the logging setup itself
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_filename}")
    logger.debug(f"Console log level: {log_level}")
    logger.debug(f"File log level: DEBUG")
    logger.debug(f"Log file path: {Path(log_filename).absolute()}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate semantic layer from Northwind database",
        epilog="Example: python main.py --output output/my_layer.json --log-level DEBUG --no-cache"
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
        help="Logging level (default: DEBUG).",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable LLM response caching"
    )
    parser.add_argument(
        "--version", action="version", version="Semantic Layer Pipeline v1.0"
    )
    return parser.parse_args()


def main() -> None:
    """Main execution function."""
    from datetime import datetime
    startup_time = datetime.now()

    args = parse_arguments()
    setup_logging(args.log_level)

    logger = logging.getLogger(__name__)
    logger.info("=== SEMANTIC LAYER PIPELINE STARTUP ===")
    logger.info(f"Startup time: {startup_time.isoformat()}")
    logger.info(f"Log level: {args.log_level}")
    logger.info(f"Output path: {args.output}")
    logger.info(f"Cache disabled: {args.no_cache}")
    logger.info(f"Python version: {sys.version}")

    try:
        # Initialize configuration
        logger.info("Initializing configuration...")
        config = Config()

        # Log configuration details
        logger.debug(f"Database connection: {config.database_config.connection_string}")
        logger.debug(f"LLM provider: {config.llm_config.provider}")
        logger.debug(f"LLM model: {config.llm_config.model}")
        logger.debug(f"LLM max tokens: {config.llm_config.max_tokens}")
        logger.debug(f"LLM temperature: {config.llm_config.temperature}")
        logger.debug(f"Original cache setting: {config.llm_config.cache_enabled}")

        if args.no_cache:
            config.llm_config.cache_enabled = False
            logger.info("LLM cache disabled via command line flag")
        else:
            logger.info(f"LLM cache enabled: {config.llm_config.cache_enabled}")

        # Create output directory
        output_path = Path(args.output)
        logger.info(f"Creating output directory: {output_path.parent}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Output directory created/confirmed: {output_path.parent.absolute()}")

        # Initialize and run pipeline
        logger.info("Initializing pipeline orchestrator...")
        orchestrator = PipelineOrchestrator(config)

        logger.info("Starting pipeline execution...")
        pipeline_start = datetime.now()
        results = orchestrator.run_pipeline(str(output_path))
        pipeline_time = (datetime.now() - pipeline_start).total_seconds()

        # Report final results
        logger.info("=== PIPELINE EXECUTION COMPLETED ====")
        logger.info(f"Total pipeline time: {pipeline_time:.2f} seconds")
        logger.info(f"Generated entities: {results['entity_count']}")
        logger.info(f"Valid entities: {results['valid_entity_count']}")
        logger.info(f"Validation passed: {results['validation_passed']}")
        logger.info(f"Warning count: {len(results.get('warnings', []))}")
        logger.info(f"Output saved to: {args.output}")

        if results.get('entity_names'):
            logger.info(f"Generated entity names: {', '.join(results['entity_names'])}")

        if results.get('warnings'):
            logger.warning("Pipeline warnings:")
            for warning in results['warnings']:
                logger.warning(f"  - {warning}")

        total_time = (datetime.now() - startup_time).total_seconds()
        logger.info(f"Total execution time (including startup): {total_time:.2f} seconds")
        logger.info("=== SEMANTIC LAYER PIPELINE COMPLETED SUCCESSFULLY ===")

    except KeyboardInterrupt:
        execution_time = (datetime.now() - startup_time).total_seconds()
        logger.warning(f"Pipeline interrupted by user after {execution_time:.2f} seconds")
        sys.exit(130)
    except Exception as e:
        execution_time = (datetime.now() - startup_time).total_seconds()
        logger.error("=== PIPELINE EXECUTION FAILED ===")
        logger.error(f"Execution time before failure: {execution_time:.2f} seconds")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")

        # Log traceback for debugging
        import traceback
        logger.error("Full traceback:")
        for line in traceback.format_exc().splitlines():
            logger.error(f"  {line}")

        sys.exit(1)


if __name__ == "__main__":
    main()
