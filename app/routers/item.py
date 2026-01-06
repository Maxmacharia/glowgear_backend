from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemResponse

router = APIRouter(prefix="/items", tags=["Items"])

@router.post("/", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    existing_item = db.query(Item).filter(Item.name == item.name).first()

    if existing_item:
        existing_item.quantity += item.quantity
        existing_item.cost_price = item.cost_price
        db.commit()
        db.refresh(existing_item)
        return existing_item

    new_item = Item(
        name=item.name,
        quantity=item.quantity,
        cost_price=item.cost_price
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.get("/", response_model=list[ItemResponse])
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()

@router.put("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: str,
    item: ItemCreate,
    db: Session = Depends(get_db)
):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db_item.name = item.name
    db_item.quantity = item.quantity
    db_item.cost_price = item.cost_price

    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def delete_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        db.delete(item)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Item cannot be deleted because it is referenced in transactions"
        )

    return {"message": "Item deleted successfully"}
