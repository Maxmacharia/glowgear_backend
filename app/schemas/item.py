from pydantic import BaseModel
from uuid import UUID

class ItemCreate(BaseModel):
    name: str
    quantity: int
    cost_price: float

class ItemResponse(ItemCreate):
    id: UUID

    class Config:
        from_attributes = True
