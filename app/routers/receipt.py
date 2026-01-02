from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date
from decimal import Decimal

from app.core.deps import get_db
from app.models.item import Item
from app.models.receipt import Receipt, ReceiptItem
from app.models.inventory_transaction import InventoryTransaction
from app.schemas.receipt import ReceiptCreate, ReceiptResponse

router = APIRouter(prefix="/receipts", tags=["Receipts"])


# -------------------------------
# CREATE RECEIPT
# -------------------------------
@router.post("/", response_model=ReceiptResponse)
def create_receipt(receipt: ReceiptCreate, db: Session = Depends(get_db)):
    if not receipt.items:
        raise HTTPException(status_code=400, detail="Receipt must contain items")

    total_amount = Decimal("0.00")
    total_profit = Decimal("0.00")

    receipt_db = Receipt(
        total_amount=Decimal("0.00"),
        total_profit=Decimal("0.00"),
    )
    db.add(receipt_db)
    db.flush()  # ensures receipt_db.id exists

    for entry in receipt.items:
        item = db.query(Item).filter(Item.id == entry.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        if item.quantity < entry.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {item.name}"
            )

        # 🔻 Deduct stock immediately
        item.quantity -= entry.quantity

        line_total = Decimal(str(entry.selling_price)) * entry.quantity
        profit = (Decimal(str(entry.selling_price)) - Decimal(str(item.cost_price))) * entry.quantity

        total_amount += line_total
        total_profit += profit

        db.add(
            ReceiptItem(
                receipt_id=receipt_db.id,
                item_id=item.id,
                quantity=entry.quantity,
                selling_price=Decimal(str(entry.selling_price)),
                cost_price=item.cost_price,
            )
        )

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=-entry.quantity,
                reason="receipt_create",
            )
        )

    receipt_db.total_amount = total_amount
    receipt_db.total_profit = total_profit

    db.commit()
    db.refresh(receipt_db)
    return receipt_db


# -------------------------------
# GET RECEIPTS
# -------------------------------
@router.get("/", response_model=list[ReceiptResponse])
def get_receipts(
    receipt_date: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Receipt).options(joinedload(Receipt.items))

    if receipt_date:
        query = query.filter(func.date(Receipt.created_at) == receipt_date)

    return query.order_by(Receipt.created_at.desc()).all()


# -------------------------------
# UPDATE RECEIPT
# -------------------------------
@router.put("/{receipt_id}", response_model=ReceiptResponse)
def update_receipt(
    receipt_id: str,
    receipt: ReceiptCreate,
    db: Session = Depends(get_db),
):
    db_receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not db_receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # 🔁 Restore old stock
    old_items = db.query(ReceiptItem).filter(
        ReceiptItem.receipt_id == receipt_id
    ).all()

    for old in old_items:
        item = db.query(Item).filter(Item.id == old.item_id).first()
        item.quantity += old.quantity

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=old.quantity,
                reason="receipt_update_restore",
            )
        )

    db.query(ReceiptItem).filter(
        ReceiptItem.receipt_id == receipt_id
    ).delete()

    total_amount = Decimal("0.00")
    total_profit = Decimal("0.00")

    # 🔻 Apply new items
    for entry in receipt.items:
        item = db.query(Item).filter(Item.id == entry.item_id).first()
        if not item or item.quantity < entry.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        item.quantity -= entry.quantity

        line_total = Decimal(str(entry.selling_price)) * entry.quantity
        profit = (Decimal(str(entry.selling_price)) - Decimal(str(item.cost_price))) * entry.quantity

        total_amount += line_total
        total_profit += profit

        db.add(
            ReceiptItem(
                receipt_id=receipt_id,
                item_id=item.id,
                quantity=entry.quantity,
                selling_price=Decimal(str(entry.selling_price)),
                cost_price=item.cost_price,
            )
        )

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=-entry.quantity,
                reason="receipt_update_apply",
            )
        )

    db_receipt.total_amount = total_amount
    db_receipt.total_profit = total_profit

    db.commit()
    db.refresh(db_receipt)
    return db_receipt


# -------------------------------
# DELETE RECEIPT
# -------------------------------
@router.delete("/{receipt_id}")
def delete_receipt(receipt_id: str, db: Session = Depends(get_db)):
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    items = db.query(ReceiptItem).filter(
        ReceiptItem.receipt_id == receipt_id
    ).all()

    # 🔁 Restore stock
    for ri in items:
        item = db.query(Item).filter(Item.id == ri.item_id).first()
        item.quantity += ri.quantity

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=ri.quantity,
                reason="receipt_delete",
            )
        )

    db.query(ReceiptItem).filter(
        ReceiptItem.receipt_id == receipt_id
    ).delete()

    db.delete(receipt)
    db.commit()

    return {"message": "Receipt deleted successfully"}
