from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Message(BaseModel):
    message: str


class Paginated(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int


class Timestamped(BaseModel):
    created_on: datetime = Field(default_factory=datetime.utcnow)

