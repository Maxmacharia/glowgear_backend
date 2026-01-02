from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.core.deps import get_db
from app.models.item import Item
from app.models.invoice import Invoice, InvoiceItem, InvoicePayment
from app.models.inventory_transaction import InventoryTransaction
from app.schemas.invoice import (
    InvoiceCreate,
    InvoicePaymentCreate,
    InvoiceResponse
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])

@router.post("/", response_model=InvoiceResponse)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    total_amount = 0
    total_profit = 0

    invoice_db = Invoice(
        client_name=invoice.client_name,
        total_amount=0,
        total_profit=0,
        status="unpaid"
    )
    db.add(invoice_db)
    db.flush()

    for entry in invoice.items:
        item = db.query(Item).filter(Item.id == entry.item_id).first()
        if not item or item.quantity < entry.quantity:
            raise HTTPException(status_code=400, detail="Invalid stock")

        item.quantity -= entry.quantity

        total_amount += entry.selling_price * entry.quantity
        total_profit += (
            (entry.selling_price - float(item.cost_price)) * entry.quantity
        )

        db.add(
            InvoiceItem(
                invoice_id=invoice_db.id,
                item_id=item.id,
                quantity=entry.quantity,
                selling_price=entry.selling_price,
                cost_price=item.cost_price
            )
        )

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=-entry.quantity,
                reason="invoice",
                reference_id=invoice_db.id
            )
        )

    invoice_db.total_amount = total_amount
    invoice_db.total_profit = total_profit

    db.commit()
    db.refresh(invoice_db)
    return invoice_db

@router.get("/", response_model=list[InvoiceResponse])
def get_invoices(
    invoice_date: date | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Invoice)

    if invoice_date:
        query = query.filter(Invoice.created_at.cast(date) == invoice_date)

    return query.all()

@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: str,
    invoice: InvoiceCreate,
    db: Session = Depends(get_db)
):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    items = db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice_id
    ).all()

    for it in items:
        item = db.query(Item).filter(Item.id == it.item_id).first()
        item.quantity += it.quantity

    db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice_id
    ).delete()

    db_invoice.total_amount = 0
    db_invoice.total_profit = 0

    for entry in invoice.items:
        item = db.query(Item).filter(Item.id == entry.item_id).first()
        if item.quantity < entry.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        item.quantity -= entry.quantity

        db_invoice.total_amount += entry.selling_price * entry.quantity
        db_invoice.total_profit += (
            (entry.selling_price - float(item.cost_price)) * entry.quantity
        )

        db.add(
            InvoiceItem(
                invoice_id=invoice_id,
                item_id=item.id,
                quantity=entry.quantity,
                selling_price=entry.selling_price,
                cost_price=item.cost_price
            )
        )

    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    items = db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice_id
    ).all()

    for it in items:
        item = db.query(Item).filter(Item.id == it.item_id).first()
        item.quantity += it.quantity

    db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice_id
    ).delete()

    db.delete(invoice)
    db.commit()
    return {"message": "Invoice deleted successfully"}

@router.post("/{invoice_id}/payments")
def add_payment(
    invoice_id: str,
    payment: InvoicePaymentCreate,
    db: Session = Depends(get_db)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.add(
        InvoicePayment(
            invoice_id=invoice_id,
            amount=payment.amount
        )
    )

    total_paid = sum(
        p.amount for p in db.query(InvoicePayment)
        .filter(InvoicePayment.invoice_id == invoice_id)
        .all()
    ) + payment.amount

    if total_paid >= invoice.total_amount:
        invoice.status = "paid"
    elif total_paid > 0:
        invoice.status = "partial"

    db.commit()
    return {"message": "Payment recorded"}
