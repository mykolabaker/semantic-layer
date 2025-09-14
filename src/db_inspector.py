"""
Database introspection module for extracting schema information,
relationships, and sample data from the Northwind database.
"""

from typing import Dict, List, Any, Optional
import sqlitecloud
from dataclasses import dataclass


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None


@dataclass
class TableInfo:
    """Complete information about a database table."""
    name: str
    columns: List[ColumnInfo]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
    sample_data: List[Dict[str, Any]]
    row_count: int


class DatabaseInspector:
    """Handles all database introspection operations."""

    def __init__(self, connection_string: str):
        """Initialize database inspector with connection string."""
        self.connection_string = connection_string
        self.connection = None

    def connect(self) -> None:
        """Establish connection to the database."""
        pass

    def disconnect(self) -> None:
        """Close database connection."""
        pass

    def get_table_names(self) -> List[str]:
        """Retrieve list of all table names in the database."""
        pass

    def get_table_schema(self, table_name: str) -> List[ColumnInfo]:
        """Extract complete schema information for a specific table."""
        pass

    def get_foreign_key_relationships(self, table_name: str) -> List[Dict[str, str]]:
        """Get all foreign key relationships for a table."""
        pass

    def get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table."""
        pass

    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve sample rows from a table."""
        pass

    def get_column_statistics(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """Get basic statistics for a column (distinct count, nulls, etc.)."""
        pass

    def get_table_info(self, table_name: str) -> TableInfo:
        """Get complete information about a table."""
        pass

    def extract_all_metadata(self) -> Dict[str, Any]:
        """Extract all database metadata and return as structured dictionary."""
        pass

    def save_schema_context(self, output_path: str) -> None:
        """Save extracted metadata to JSON file for reuse."""
        pass