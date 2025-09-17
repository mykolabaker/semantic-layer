import os
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add src to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import main

@pytest.fixture
def task_test_environment():
    """Set up test environment for a single test function."""
    output_dir = Path("output")
    db_path = Path("tests/northwind.db").resolve()

    if not db_path.exists():
        pytest.fail(f"Database file not found at {db_path}")

    # Clean up and create directories
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Set environment variables
    os.environ["DATABASE_CONNECTION_STRING"] = f"sqlite:///{db_path}"
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["CACHE_ENABLED"] = "false"

    yield output_dir

    # Teardown
    shutil.rmtree(output_dir)
    del os.environ["DATABASE_CONNECTION_STRING"]
    del os.environ["LLM_PROVIDER"]
    del os.environ["OPENAI_API_KEY"]
    del os.environ["CACHE_ENABLED"]

def _get_mock_llm_service():
    """Creates a mock LLMService."""
    mock_llm_service = MagicMock()
    mock_llm_service.generate_entity_identification.return_value = {
        "entities": [
            {"name": "customers", "description": "Customer data"},
            {"name": "products", "description": "Product data"},
            {"name": "orders", "description": "Order data"},
        ]
    }

    def mock_generate_details(entity_name, entity, schema_context):
        id_mapping = {
            "customers": "CustomerID",
            "products": "ProductID",
            "orders": "OrderID",
        }
        return {
            "description": f"Details for {entity_name}",
            "base_query": f'SELECT * FROM "{entity_name.capitalize()}"',
            "attributes": { "id": { "name": "ID", "sql": id_mapping.get(entity_name, "id"), "description": "Identifier"}},
            "relations": {}
        }

    mock_llm_service.generate_entity_details.side_effect = mock_generate_details
    return mock_llm_service

@patch("src.orchestrator.LLMService")
def test_all_output_files_are_created(mock_llm_service_class, task_test_environment):
    """Test that the pipeline creates all expected output files."""
    mock_llm_service_class.return_value = _get_mock_llm_service()
    output_dir = task_test_environment

    output_file = output_dir / "semantic_layer.json"

    test_args = ["main.py", "-o", str(output_file)]
    with patch.object(sys, 'argv', test_args):
        main()

    assert (output_dir / "semantic_layer.json").exists()
    assert (output_dir / "schema_context.json").exists()
    assert (output_dir / "validation_report.txt").exists()
    assert (output_dir / "pipeline_report.txt").exists()

def test_documentation_exists():
    """Test that the methodology documentation file exists and is not empty."""
    doc_file = Path("docs/methodology.md")
    assert doc_file.exists()
    assert doc_file.stat().st_size > 0, "The methodology.md file is empty."

import sqlite3

@patch("src.orchestrator.LLMService")
def test_semantic_layer_content(mock_llm_service_class, task_test_environment):
    """Test the content of the generated semantic layer for correctness and SQL validity."""
    mock_llm_service_class.return_value = _get_mock_llm_service()
    output_dir = task_test_environment
    output_file = output_dir / "semantic_layer.json"

    test_args = ["main.py", "-o", str(output_file)]
    with patch.object(sys, 'argv', test_args):
        main()

    with open(output_file, "r") as f:
        data = json.load(f)

    assert len(data["entities"]) >= 3  # Mock LLM returns 3 entities

    db_path = os.environ["DATABASE_CONNECTION_STRING"].replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for entity_name, entity in data["entities"].items():
        # Test base_query
        try:
            cursor.execute(f"SELECT * FROM ({entity['base_query']}) LIMIT 1")
        except sqlite3.OperationalError as e:
            pytest.fail(f"Entity '{entity_name}' has an invalid base_query: {e}")

        # Test attributes
        for attr_name, attr in entity["attributes"].items():
            try:
                # Check if the attribute's SQL is a valid expression
                query = f"SELECT {attr['sql']} FROM ({entity['base_query']}) LIMIT 1"
                cursor.execute(query)
            except sqlite3.OperationalError as e:
                pytest.fail(f"Attribute '{attr_name}' in entity '{entity_name}' has invalid SQL: {e}")

    conn.close()