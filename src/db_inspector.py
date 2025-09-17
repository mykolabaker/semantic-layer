"""
Database introspection module for extracting schema information,
relationships, and sample data from the Northwind database.
"""

from typing import Dict, List, Any, Optional
import sqlite3
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
        self.logger.info(f"Attempting to connect to database: {self.connection_string}")
        try:
            # Support local sqlite file paths
            db_path = self.connection_string
            if db_path.startswith("sqlite:///"):
                db_path = db_path[10:]
                self.logger.debug(f"Converted SQLite URL to path: {db_path}")

            self.logger.debug(f"Opening SQLite database at: {db_path}")
            self.connection = sqlite3.connect(db_path)

            # Test the connection
            cursor = self.connection.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            self.logger.info(f"Database connection established successfully (SQLite version: {version})")

        except Exception as e:
            self.logger.error(f"Failed to connect to database '{self.connection_string}': {e}")
            self.logger.error(f"Error type: {type(e).__name__}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.connection:
            self.logger.info("Closing database connection...")
            self.connection.close()
            self.connection = None
            self.logger.info("Database connection closed successfully")
        else:
            self.logger.debug("No active database connection to close")

    def get_table_names(self) -> List[str]:
        """Retrieve list of all table names in the database."""
        self.logger.debug("Retrieving table names from database")
        if not self.connection:
            self.logger.debug("No connection available, establishing new connection")
            self.connect()

        if self.connection is None:
            raise RuntimeError("Database connection not established")

        self.logger.debug("Executing query to get table names")
        cursor = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        )
        tables = [row[0] for row in cursor.fetchall()]
        self.logger.info(f"Found {len(tables)} tables: {tables}")

        # Log table types for debugging
        system_tables = [t for t in tables if t.startswith('sqlite_')]
        user_tables = [t for t in tables if not t.startswith('sqlite_')]
        self.logger.debug(f"System tables: {system_tables}")
        self.logger.debug(f"User tables: {user_tables}")

        return tables

    def get_table_schema(self, table_name: str) -> List[ColumnInfo]:
        """Extract complete schema information for a specific table."""
        self.logger.debug(f"Extracting schema for table: {table_name}")
        if not self.connection:
            self.connect()

        # Get column information
        if self.connection is None:
            raise RuntimeError("Database connection not established")

        self.logger.debug(f"Getting column info for table: {table_name}")
        cursor = self.connection.execute(f'PRAGMA table_info("{table_name}")')
        columns = []

        for row in cursor.fetchall():
            cid, name, data_type, not_null, default_value, pk = row
            self.logger.debug(f"Column: {name}, Type: {data_type}, PK: {bool(pk)}, Not Null: {bool(not_null)}")
            columns.append(
                ColumnInfo(
                    name=name,
                    data_type=data_type,
                    is_nullable=not not_null,
                    is_primary_key=bool(pk),
                    is_foreign_key=False,  # Will be updated with FK info
                )
            )

        self.logger.debug(f"Found {len(columns)} columns in table {table_name}")

        # Add foreign key information
        self.logger.debug(f"Getting foreign key relationships for table: {table_name}")
        fk_info = self.get_foreign_key_relationships(table_name)
        self.logger.debug(f"Found {len(fk_info)} foreign key relationships")

        for fk in fk_info:
            for col in columns:
                if col.name == fk["from"]:
                    col.is_foreign_key = True
                    col.foreign_table = fk["table"]
                    col.foreign_column = fk["to"]
                    self.logger.debug(f"Column {col.name} references {fk['table']}.{fk['to']}")

        return columns

    def get_foreign_key_relationships(self, table_name: str) -> List[Dict[str, str]]:
        """Get all foreign key relationships for a table."""
        self.logger.debug(f"Getting foreign key relationships for table: {table_name}")
        if not self.connection:
            self.connect()

        if self.connection is None:
            raise RuntimeError("Database connection not established")
        cursor = self.connection.execute(f'PRAGMA foreign_key_list("{table_name}")')
        foreign_keys = []

        for row in cursor.fetchall():
            id_, seq, table, from_col, to_col, on_update, on_delete, match = row
            fk_relationship = {"from": from_col, "table": table, "to": to_col}
            foreign_keys.append(fk_relationship)
            self.logger.debug(f"FK: {table_name}.{from_col} -> {table}.{to_col}")

        if foreign_keys:
            self.logger.debug(f"Table {table_name} has {len(foreign_keys)} foreign key relationships")
        else:
            self.logger.debug(f"Table {table_name} has no foreign key relationships")

        return foreign_keys

    def get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table."""
        columns = self.get_table_schema(table_name)
        return [col.name for col in columns if col.is_primary_key]

    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve sample rows from a table."""
        self.logger.debug(f"Getting {limit} sample rows from table: {table_name}")
        if not self.connection:
            self.connect()

        if self.connection is None:
            raise RuntimeError("Database connection not established")

        cursor = self.connection.execute(f'SELECT * FROM "{table_name}" LIMIT {limit}')
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        self.logger.debug(f"Retrieved {len(rows)} sample rows with {len(columns)} columns")
        self.logger.debug(f"Column names: {columns}")

        sample_data = []
        for i, row in enumerate(rows):
            row_dict = {}
            for col, value in zip(columns, row):
                # Convert bytes to string representation for JSON serialization
                if isinstance(value, bytes):
                    row_dict[col] = f"<BLOB data: {len(value)} bytes>"
                else:
                    row_dict[col] = value
            sample_data.append(row_dict)

        # Log first sample row for debugging (with truncated values)
        if sample_data:
            first_row = sample_data[0]
            truncated_row = {k: (str(v)[:50] + '...' if isinstance(v, str) and len(str(v)) > 50 else v)
                           for k, v in first_row.items()}
            self.logger.debug(f"Sample row from {table_name}: {truncated_row}")

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
            FROM "{table_name}"
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
        self.logger.debug(f"Getting complete table info for: {table_name}")

        self.logger.debug(f"Getting schema for {table_name}")
        columns = self.get_table_schema(table_name)

        self.logger.debug(f"Getting primary keys for {table_name}")
        primary_keys = self.get_primary_keys(table_name)

        self.logger.debug(f"Getting foreign keys for {table_name}")
        foreign_keys = self.get_foreign_key_relationships(table_name)

        self.logger.debug(f"Getting sample data for {table_name}")
        sample_data = self.get_sample_data(table_name)

        # Get row count
        if self.connection is None:
            raise RuntimeError("Database connection not established")

        self.logger.debug(f"Getting row count for {table_name}")
        cursor = self.connection.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = cursor.fetchone()[0]

        self.logger.debug(f"Table {table_name} summary: {len(columns)} columns, {len(primary_keys)} PK columns, {len(foreign_keys)} FK relationships, {row_count} rows")

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
        from datetime import datetime
        start_time = datetime.now()
        self.logger.info("Starting database metadata extraction")

        tables = self.get_table_names()
        self.logger.info(f"Will extract metadata for {len(tables)} tables")

        metadata: Dict[str, Any] = {
            "database_name": "northwind.db",
            "table_count": len(tables),
            "tables": {},
            "extraction_timestamp": start_time.isoformat(),
        }

        total_rows = 0
        processed_tables = 0

        for i, table_name in enumerate(tables, 1):
            table_start = datetime.now()
            self.logger.info(f"[{i}/{len(tables)}] Extracting metadata for table: {table_name}")

            try:
                table_info = self.get_table_info(table_name)

                table_time = (datetime.now() - table_start).total_seconds()
                self.logger.debug(f"Table {table_name} processed in {table_time:.2f} seconds")

                metadata["tables"][table_name] = {
                    "name": table_info.name,
                    "columns": [asdict(col) for col in table_info.columns],
                    "primary_keys": table_info.primary_keys,
                    "foreign_keys": table_info.foreign_keys,
                    "sample_data": table_info.sample_data[:3],  # Limit for LLM context
                    "row_count": table_info.row_count,
                }

                total_rows += table_info.row_count
                processed_tables += 1

                # Log progress for large operations
                if i % 5 == 0 or i == len(tables):
                    elapsed = (datetime.now() - start_time).total_seconds()
                    self.logger.info(f"Progress: {i}/{len(tables)} tables processed in {elapsed:.2f} seconds")

            except Exception as e:
                self.logger.error(f"Failed to extract metadata for table {table_name}: {e}")
                continue

        extraction_time = (datetime.now() - start_time).total_seconds()
        metadata["extraction_duration_seconds"] = extraction_time
        metadata["total_rows"] = total_rows

        self.logger.info(f"Database metadata extraction completed in {extraction_time:.2f} seconds")
        self.logger.info(f"Successfully processed {processed_tables}/{len(tables)} tables")
        self.logger.info(f"Total rows across all tables: {total_rows}")

        # Log table size distribution
        if metadata["tables"]:
            row_counts = [table["row_count"] for table in metadata["tables"].values()]
            avg_rows = sum(row_counts) / len(row_counts)
            max_rows = max(row_counts)
            largest_table = max(metadata["tables"].items(), key=lambda x: x[1]["row_count"])
            self.logger.debug(f"Table size stats - Average: {avg_rows:.1f} rows, Max: {max_rows} rows (table: {largest_table[0]})")

        return metadata

    def save_schema_context(self, output_path: str) -> None:
        """Save extracted metadata to JSON file for reuse."""
        metadata = self.extract_all_metadata()
        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        self.logger.info(f"Schema context saved to {output_path}")
