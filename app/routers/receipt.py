from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date
from decimal import Decimal

from app.core.deps import get_db
from app.models.item import Item
from app.models.receipt import Receipt, ReceiptItem
from app.models.inventory_transaction import InventoryTransaction
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptResponse,
    ReceiptItemResponse,
)

router = APIRouter(prefix="/receipts", tags=["Receipts"])


# -------------------------------
# HELPER: BUILD RESPONSE
# -------------------------------
def build_receipt_response(receipt: Receipt) -> ReceiptResponse:
    items = []

    for ri in receipt.items:
        items.append(
            ReceiptItemResponse(
                item_id=ri.item_id,
                item_name=ri.item.name,
                quantity=ri.quantity,
                selling_price=float(ri.selling_price),
                line_total=float(ri.selling_price * ri.quantity),
            )
        )

    return ReceiptResponse(
        id=receipt.id,
        client_name=receipt.client_name,
        total_amount=float(receipt.total_amount),
        created_at=receipt.created_at,
        items=items,
    )


# -------------------------------
# CREATE RECEIPT
# -------------------------------
@router.post("/", response_model=ReceiptResponse)
def create_receipt(receipt: ReceiptCreate, db: Session = Depends(get_db)):
    if not receipt.items:
        raise HTTPException(status_code=400, detail="Receipt must contain items")

    total_amount = Decimal("0.00")

    receipt_db = Receipt(
        client_name=receipt.client_name,
        total_amount=Decimal("0.00"),
    )

    db.add(receipt_db)
    db.flush()

    for entry in receipt.items:
        item = db.query(Item).filter(Item.id == entry.item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        if item.quantity < entry.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {item.name}"
            )

        # 🔻 Deduct stock
        item.quantity -= entry.quantity

        line_total = Decimal(str(entry.selling_price)) * entry.quantity
        total_amount += line_total

        db.add(
            ReceiptItem(
                receipt_id=receipt_db.id,
                item_id=item.id,
                quantity=entry.quantity,
                selling_price=Decimal(str(entry.selling_price)),
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

    db.commit()
    db.refresh(receipt_db)

    return build_receipt_response(receipt_db)


# -------------------------------
# GET RECEIPTS
# -------------------------------
@router.get("/", response_model=list[ReceiptResponse])
def get_receipts(
    receipt_date: date | None = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Receipt)
        .options(joinedload(Receipt.items).joinedload(ReceiptItem.item))
    )

    if receipt_date:
        query = query.filter(func.date(Receipt.created_at) == receipt_date)

    receipts = query.order_by(Receipt.created_at.desc()).all()

    return [build_receipt_response(r) for r in receipts]


# -------------------------------
# UPDATE RECEIPT
# -------------------------------
@router.put("/{receipt_id}", response_model=ReceiptResponse)
def update_receipt(
    receipt_id: str,
    receipt: ReceiptCreate,
    db: Session = Depends(get_db),
):
    receipt_db = (
        db.query(Receipt)
        .options(joinedload(Receipt.items))
        .filter(Receipt.id == receipt_id)
        .first()
    )

    if not receipt_db:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # 🔁 Restore stock
    for ri in receipt_db.items:
        item = db.query(Item).filter(Item.id == ri.item_id).first()
        item.quantity += ri.quantity

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=ri.quantity,
                reason="receipt_update_restore",
            )
        )

    db.query(ReceiptItem).filter(
        ReceiptItem.receipt_id == receipt_id
    ).delete()

    total_amount = Decimal("0.00")

    for entry in receipt.items:
        item = db.query(Item).filter(Item.id == entry.item_id).first()
        if not item or item.quantity < entry.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        item.quantity -= entry.quantity

        line_total = Decimal(str(entry.selling_price)) * entry.quantity
        total_amount += line_total

        db.add(
            ReceiptItem(
                receipt_id=receipt_id,
                item_id=item.id,
                quantity=entry.quantity,
                selling_price=Decimal(str(entry.selling_price)),
            )
        )

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=-entry.quantity,
                reason="receipt_update_apply",
            )
        )

    receipt_db.client_name = receipt.client_name
    receipt_db.total_amount = total_amount

    db.commit()
    db.refresh(receipt_db)

    return build_receipt_response(receipt_db)


# -------------------------------
# DELETE RECEIPT
# -------------------------------
@router.delete("/{receipt_id}")
def delete_receipt(receipt_id: str, db: Session = Depends(get_db)):
    receipt = (
        db.query(Receipt)
        .options(joinedload(Receipt.items))
        .filter(Receipt.id == receipt_id)
        .first()
    )

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    for ri in receipt.items:
        item = db.query(Item).filter(Item.id == ri.item_id).first()
        item.quantity += ri.quantity

        db.add(
            InventoryTransaction(
                item_id=item.id,
                quantity_change=ri.quantity,
                reason="receipt_delete",
            )
        )

    db.delete(receipt)
    db.commit()

    return {"message": "Receipt deleted successfully"}
