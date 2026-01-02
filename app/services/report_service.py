from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import date
from app.models.receipt import Receipt
from app.models.invoice import Invoice
from app.models.expense import Expense


def get_daily_profit_loss(db: Session, target_date: date):
    receipts_profit = (
        db.query(func.coalesce(func.sum(Receipt.total_profit), 0))
        .filter(cast(Receipt.created_at, Date) == target_date)
        .scalar()
    )

    invoices_profit = (
        db.query(func.coalesce(func.sum(Invoice.total_profit), 0))
        .filter(cast(Invoice.created_at, Date) == target_date)
        .scalar()
    )

    expenses_total = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(cast(Expense.created_at, Date) == target_date)
        .scalar()
    )

    net_profit = receipts_profit + invoices_profit - expenses_total

    return {
        "date": target_date,
        "receipts_profit": float(receipts_profit),
        "invoices_profit": float(invoices_profit),
        "expenses": float(expenses_total),
        "net_profit": float(net_profit),
    }
