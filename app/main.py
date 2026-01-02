from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine

from app.routers.item import router as item_router
from app.routers.expense import router as expense_router
from app.routers.receipt import router as receipt_router
from app.routers.invoice import router as invoice_router
from app.routers.report import router as report_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inventory & Accounting System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", 
                   "https://glowgear-front.vercel.app/"],  # Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(item_router)
app.include_router(expense_router)
app.include_router(receipt_router)
app.include_router(invoice_router)
app.include_router(report_router)

@app.get("/")
def root():
    return {"status": "running"}
