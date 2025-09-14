"""
Pydantic models for data validation and structure enforcement
of the semantic layer JSON output.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict
from datetime import datetime


class AttributeModel(BaseModel):
    """Model for entity attribute definition."""

    name: str = Field(..., description="Human-readable attribute name")
    description: str = Field(..., description="Description of the attribute")
    sql: str = Field(..., description="SQL expression for the attribute")


class RelationModel(BaseModel):
    """Model for entity relationship definition."""

    name: str = Field(..., description="Human-readable relation name")
    description: str = Field(..., description="Description of the relationship")
    target_entity: str = Field(..., description="Target entity name")
    sql: str = Field(..., description="SQL join condition")


class EntityModel(BaseModel):
    """Model for complete entity definition."""

    description: str = Field(..., description="Entity description")
    base_query: str = Field(..., description="Base SQL query for the entity")
    attributes: Dict[str, AttributeModel] = Field(..., description="Entity attributes")
    relations: Dict[str, RelationModel] = Field(
        default_factory=dict, description="Entity relationships"
    )

    @validator("base_query")
    def validate_base_query(cls, v):
        """Validate that base_query is a proper SQL SELECT statement."""
        if not v.strip().upper().startswith("SELECT"):
            raise ValueError("base_query must be a SELECT statement")
        return v


class SemanticLayerModel(BaseModel):
    """Model for the complete semantic layer JSON structure."""

    generated_at: datetime = Field(
        default_factory=datetime.now, description="Generation timestamp"
    )
    database: str = Field(..., description="Source database name")
    entities: Dict[str, EntityModel] = Field(..., description="Business entities")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
