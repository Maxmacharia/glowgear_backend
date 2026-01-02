from pydantic import BaseModel
from uuid import UUID
from typing import List
from datetime import datetime


class ReceiptItemCreate(BaseModel):
    item_id: UUID
    quantity: int
    selling_price: float


class ReceiptCreate(BaseModel):
    client_name: str | None = None
    items: List[ReceiptItemCreate]


class ReceiptItemResponse(BaseModel):
    item_id: UUID
    item_name: str
    quantity: int
    selling_price: float
    line_total: float

    class Config:
        from_attributes = True


class ReceiptResponse(BaseModel):
    id: UUID
    client_name: str | None
    total_amount: float
    created_at: datetime
    items: List[ReceiptItemResponse]

    class Config:
        from_attributes = True
