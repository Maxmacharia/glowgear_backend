import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:44190-@localhost:5432/inventory_db"
)
