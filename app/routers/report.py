from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date

from app.core.deps import get_db
from app.models.receipt import Receipt, ReceiptItem
from app.models.item import Item
from app.models.expense import Expense

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily")
def daily_report(
    report_date: date,
    db: Session = Depends(get_db),
):
    # -------------------------------------------------
    # RECEIPTS + ITEMS SOLD ON THIS DAY
    # -------------------------------------------------
    receipts = (
        db.query(Receipt)
        .options(
            joinedload(Receipt.items).joinedload(ReceiptItem.item)
        )
        .filter(func.date(Receipt.created_at) == report_date)
        .order_by(Receipt.created_at)
        .all()
    )

    receipts_data = []
    total_selling = 0.0
    total_buying = 0.0

    for receipt in receipts:
        receipt_total = 0.0
        items_data = []

        for ri in receipt.items:
            selling_total = float(ri.selling_price) * ri.quantity
            buying_total = float(ri.item.cost_price) * ri.quantity

            receipt_total += selling_total
            total_selling += selling_total
            total_buying += buying_total

            items_data.append(
                {
                    "item_name": ri.item.name,
                    "quantity": ri.quantity,
                    "selling_price": float(ri.selling_price),
                    "buying_price": float(ri.item.cost_price),
                    "line_total": round(selling_total, 2),
                }
            )

        receipts_data.append(
            {
                "receipt_id": receipt.id,
                "client_name": receipt.client_name,
                "created_at": receipt.created_at,
                "items": items_data,
                "receipt_total": round(receipt_total, 2),
            }
        )

    # -------------------------------------------------
    # EXPENSES ON THIS DAY
    # -------------------------------------------------
    expenses = (
        db.query(Expense)
        .filter(func.date(Expense.created_at) == report_date)
        .order_by(Expense.created_at)
        .all()
    )

    expenses_data = [
        {
            "description": e.description,
            "amount": float(e.amount),
            "created_at": e.created_at,
        }
        for e in expenses
    ]

    total_expenses = sum(float(e.amount) for e in expenses)

    # -------------------------------------------------
    # FINAL RESULT (PROFIT OR LOSS)
    # -------------------------------------------------
    profit_or_loss = (total_selling - total_buying) - total_expenses

    return {
        "date": report_date,
        "receipts": receipts_data,
        "expenses": expenses_data,
        "summary": {
            "total_receipt_sales": round(total_selling, 2),
            "total_receipt_buying": round(total_buying, 2),
            "total_expenses": round(total_expenses, 2),
            "profit_or_loss": round(profit_or_loss, 2),
        },
    }
