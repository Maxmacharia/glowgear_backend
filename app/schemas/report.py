from pydantic import BaseModel
from datetime import date
from typing import List

class SoldItem(BaseModel):
    receipt_time: str
    item_id: str
    quantity: int
    buying_price: float
    selling_price: float


class DailyReportResponse(BaseModel):
    date: date
    total_sales: float
    total_buying: float
    total_expenses: float
    profit_or_loss: float
    items: List[SoldItem]
