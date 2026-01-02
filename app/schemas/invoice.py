from pydantic import BaseModel
from uuid import UUID
from typing import List
from datetime import datetime

class InvoiceItemCreate(BaseModel):
    item_id: UUID
    quantity: int
    selling_price: float


class InvoiceCreate(BaseModel):
    client_name: str
    items: List[InvoiceItemCreate]


class InvoicePaymentCreate(BaseModel):
    amount: float


class InvoiceResponse(BaseModel):
    id: UUID
    client_name: str
    total_amount: float
    total_profit: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
