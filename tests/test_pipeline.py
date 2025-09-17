
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
def test_environment():
    """Set up test environment for a single test function."""
    test_output_dir = Path("tests/output")
    db_path = Path("tests/northwind.db").resolve()

    if not db_path.exists():
        pytest.fail(f"Database file not found at {db_path}")

    # Clean up and create directories
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)
    test_output_dir.mkdir(parents=True, exist_ok=True)

    # Set environment variables
    os.environ["DATABASE_CONNECTION_STRING"] = f"sqlite:///{db_path}"
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["CACHE_ENABLED"] = "false"

    yield test_output_dir / "semantic_layer.json"

    # Teardown
    shutil.rmtree(test_output_dir)
    del os.environ["DATABASE_CONNECTION_STRING"]
    del os.environ["LLM_PROVIDER"]
    del os.environ["OPENAI_API_KEY"]
    del os.environ["CACHE_ENABLED"]

def _get_mock_llm_service(return_bad_entity=False):
    """Creates a mock LLMService with corrected SQL attributes."""
    mock_llm_service = MagicMock()

    mock_llm_service.generate_entity_identification.return_value = {
        "entities": [
            {"name": "customers", "description": "Customer data"},
            {"name": "products", "description": "Product data"},
            {"name": "orders", "description": "Order data"},
            {"name": "order_details", "description": "Order line items"},
        ]
    }

    def mock_generate_details(entity_name, entity, schema_context):
        table_map = {
            "customers": "Customers",
            "products": "Products",
            "orders": "Orders",
            "order_details": "Order Details",
        }
        id_map = {
            "customers": "CustomerID",
            "products": "ProductID",
            "orders": "OrderID",
            "order_details": "OrderID", # Part of a composite key, but fine for this test
        }

        table_name = table_map.get(entity_name, entity_name.capitalize())
        id_column = id_map.get(entity_name, "id")

        base_query = f'SELECT * FROM "{table_name}"'

        entity_details = {
            "description": f"Details for {entity_name}",
            "base_query": base_query,
            "attributes": {
                "id": {
                    "name": f"{entity_name.capitalize()} ID",
                    "sql": id_column,
                    "description": f"Unique identifier for {entity_name}"
                }
            },
            "relations": {}
        }

        if return_bad_entity and entity_name == "orders":
            entity_details["attributes"]["total_price"] = {
                "name": "Total Price",
                "sql": "SUM(Price)", # Intentionally bad SQL
                "description": "This is bad SQL"
            }

        return entity_details

    mock_llm_service.generate_entity_details.side_effect = mock_generate_details
    return mock_llm_service

@patch("src.orchestrator.LLMService")
def test_pipeline_success_scenario(mock_llm_service_class, test_environment):
    """Test the pipeline runs successfully and creates a valid output file."""
    mock_llm_service_class.return_value = _get_mock_llm_service(return_bad_entity=False)
    output_file = test_environment

    test_args = ["main.py", "-o", str(output_file)]
    with patch.object(sys, 'argv', test_args):
        main()

    assert output_file.exists()

    with open(output_file, "r") as f:
        data = json.load(f)

    assert "generated_at" in data
    assert len(data["entities"]) == 4
    assert "customers" in data["entities"]
    assert "products" in data["entities"]
    assert "orders" in data["entities"]
    assert "order_details" in data["entities"]

@patch("src.orchestrator.LLMService")
def test_pipeline_validation_failure_scenario(mock_llm_service_class, test_environment):
    """Test that the pipeline validation correctly identifies and removes a bad entity."""
    mock_llm_service_class.return_value = _get_mock_llm_service(return_bad_entity=True)
    output_file = test_environment

    test_args = ["main.py", "-o", str(output_file)]
    with patch.object(sys, 'argv', test_args):
        main()

    assert output_file.exists()

    with open(output_file, "r") as f:
        data = json.load(f)

    assert "orders" not in data["entities"]
    assert "customers" in data["entities"]
    assert "products" in data["entities"]
    assert "order_details" in data["entities"]
    assert len(data["entities"]) == 3
