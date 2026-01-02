from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from app.core.deps import get_db
from app.models.receipt import ReceiptItem, Receipt
from app.models.invoice import Invoice
from app.models.expense import Expense

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily")
def daily_report(
    report_date: date,
    db: Session = Depends(get_db),
):
    # ---- RECEIPTS ----
    receipt_items = (
        db.query(ReceiptItem)
        .join(Receipt)
        .filter(func.date(Receipt.created_at) == report_date)
        .order_by(Receipt.created_at)
        .all()
    )

    total_sales = sum(
        float(ri.selling_price) * ri.quantity
        for ri in receipt_items
    )

    total_buying = sum(
        float(ri.cost_price) * ri.quantity
        for ri in receipt_items
    )

    total_profit = total_sales - total_buying

    # ---- INVOICES ----
    invoices = (
        db.query(Invoice)
        .filter(func.date(Invoice.created_at) == report_date)
        .all()
    )
    total_invoices = sum(float(i.total_amount) for i in invoices)

    # ---- EXPENSES ----
    expenses = (
        db.query(Expense)
        .filter(func.date(Expense.created_at) == report_date)
        .all()
    )
    total_expenses = sum(float(e.amount) for e in expenses)

    return {
        "date": report_date,
        "sales": round(total_sales, 2),
        "buying": round(total_buying, 2),
        "expenses": round(total_expenses, 2),
        "invoices": round(total_invoices, 2),
        "profit": round(total_profit - total_expenses, 2),
    }
