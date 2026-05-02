from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ColumnInfo(BaseModel):
    name: str
    type: str
    nullable: bool
    default: Optional[Any] = None

class ForeignKeyInfo(BaseModel):
    column: str
    references_table: str
    references_column: str

class IndexInfo(BaseModel):
    name: str
    columns: List[str]
    unique: bool

class TableInfo(BaseModel):
    name: str
    columns: List[ColumnInfo]
    primary_key: List[str]
    foreign_keys: List[ForeignKeyInfo]
    indexes: List[IndexInfo]
    row_count: Optional[int] = None

class DatabaseInfo(BaseModel):
    dialect: str
    tables: List[TableInfo]
    notes: Dict[str, str] = {}
