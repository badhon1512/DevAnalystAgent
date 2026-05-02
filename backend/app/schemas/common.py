from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')
class ObjectResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int