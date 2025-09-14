"""
Database introspection module for extracting schema information,
relationships, and sample data from the Northwind database.
"""

from typing import Dict, List, Any, Optional
import sqlitecloud  # type: ignore
import logging
import json
from dataclasses import dataclass, asdict


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
        self.connection: Optional[Any] = None
        self.logger = logging.getLogger(__name__)

    def connect(self) -> None:
        """Establish connection to the database."""
        try:
            self.connection = sqlitecloud.connect(self.connection_string)
            self.logger.info("Database connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.logger.info("Database connection closed")

    def get_table_names(self) -> List[str]:
        """Retrieve list of all table names in the database."""
        if not self.connection:
            self.connect()

        if self.connection is None:
            raise RuntimeError("Database connection not established")
        cursor = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        tables = [row[0] for row in cursor.fetchall()]
        self.logger.info(f"Found {len(tables)} tables: {tables}")
        return tables

    def get_table_schema(self, table_name: str) -> List[ColumnInfo]:
        """Extract complete schema information for a specific table."""
        if not self.connection:
            self.connect()

        # Get column information
        if self.connection is None:
            raise RuntimeError("Database connection not established")
        cursor = self.connection.execute(f"PRAGMA table_info({table_name})")
        columns = []

        for row in cursor.fetchall():
            cid, name, data_type, not_null, default_value, pk = row
            columns.append(
                ColumnInfo(
                    name=name,
                    data_type=data_type,
                    is_nullable=not not_null,
                    is_primary_key=bool(pk),
                    is_foreign_key=False,  # Will be updated with FK info
                )
            )

        # Add foreign key information
        fk_info = self.get_foreign_key_relationships(table_name)
        for fk in fk_info:
            for col in columns:
                if col.name == fk["from"]:
                    col.is_foreign_key = True
                    col.foreign_table = fk["table"]
                    col.foreign_column = fk["to"]

        return columns

    def get_foreign_key_relationships(self, table_name: str) -> List[Dict[str, str]]:
        """Get all foreign key relationships for a table."""
        if not self.connection:
            self.connect()

        if self.connection is None:
            raise RuntimeError("Database connection not established")
        cursor = self.connection.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = []

        for row in cursor.fetchall():
            id_, seq, table, from_col, to_col, on_update, on_delete, match = row
            foreign_keys.append({"from": from_col, "table": table, "to": to_col})

        return foreign_keys

    def get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table."""
        columns = self.get_table_schema(table_name)
        return [col.name for col in columns if col.is_primary_key]

    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve sample rows from a table."""
        if not self.connection:
            self.connect()

        if self.connection is None:
            raise RuntimeError("Database connection not established")
        cursor = self.connection.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        sample_data = []
        for row in rows:
            sample_data.append(dict(zip(columns, row)))

        return sample_data

    def get_column_statistics(
        self, table_name: str, column_name: str
    ) -> Dict[str, Any]:
        """Get basic statistics for a column."""
        if not self.connection:
            self.connect()

        if self.connection is None:
            raise RuntimeError("Database connection not established")
        cursor = self.connection.execute(f"""
            SELECT
                COUNT(DISTINCT {column_name}) as distinct_count,
                COUNT({column_name}) as non_null_count,
                COUNT(*) as total_count
            FROM {table_name}
        """)

        result = cursor.fetchone()
        return {
            "distinct_count": result[0],
            "non_null_count": result[1],
            "total_count": result[2],
            "null_count": result[2] - result[1],
        }

    def get_table_info(self, table_name: str) -> TableInfo:
        """Get complete information about a table."""
        columns = self.get_table_schema(table_name)
        primary_keys = self.get_primary_keys(table_name)
        foreign_keys = self.get_foreign_key_relationships(table_name)
        sample_data = self.get_sample_data(table_name)

        # Get row count
        if self.connection is None:
            raise RuntimeError("Database connection not established")
        cursor = self.connection.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]

        return TableInfo(
            name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            sample_data=sample_data,
            row_count=row_count,
        )

    def extract_all_metadata(self) -> Dict[str, Any]:
        """Extract all database metadata and return as structured dictionary."""
        self.logger.info("Starting database metadata extraction")

        tables = self.get_table_names()
        metadata: Dict[str, Any] = {
            "database_name": "northwind.db",
            "table_count": len(tables),
            "tables": {},
        }

        for table_name in tables:
            self.logger.info(f"Extracting metadata for table: {table_name}")
            table_info = self.get_table_info(table_name)
            metadata["tables"][table_name] = {
                "name": table_info.name,
                "columns": [asdict(col) for col in table_info.columns],
                "primary_keys": table_info.primary_keys,
                "foreign_keys": table_info.foreign_keys,
                "sample_data": table_info.sample_data[:3],  # Limit for LLM context
                "row_count": table_info.row_count,
            }

        self.logger.info("Database metadata extraction completed")
        return metadata

    def save_schema_context(self, output_path: str) -> None:
        """Save extracted metadata to JSON file for reuse."""
        metadata = self.extract_all_metadata()
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        self.logger.info(f"Schema context saved to {output_path}")
