from dataclasses import dataclass, field


@dataclass
class ColumnInfo:
    name: str
    description: str
    data_type: str
    tests: list[str] = field(default_factory=list)


@dataclass
class ModelInfo:
    unique_id: str
    name: str
    schema: str
    database: str
    description: str
    materialized: str
    columns: list[ColumnInfo]
    layer: str
    path: str  # relative path from models dir, e.g. "staging/stg_orders.sql"
