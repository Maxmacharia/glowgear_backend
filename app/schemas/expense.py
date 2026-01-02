from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class ExpenseCreate(BaseModel):
    description: str
    amount: float

class ExpenseResponse(ExpenseCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
