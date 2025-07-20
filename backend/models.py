# backend/models.py

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

# Pydantic model for data validation when creating a receipt
class ReceiptCreate(BaseModel):
    filename: str
    vendor: str = Field(..., min_length=1, description="Name of the vendor/biller")
    transaction_date: datetime = Field(..., description="Date of the transaction or billing period")
    amount: float = Field(..., gt=0, description="Total amount of the receipt/bill")
    category: Optional[str] = Field(None, description="Category of the expense (e.g., Groceries, Utilities)")
    extracted_text: str = Field(..., description="Full text extracted from the receipt/bill")

    class Config:
        # This allows ORM models to be used with Pydantic
        # It means Pydantic will try to read data from ORM objects' attributes
        # rather than just dictionary keys.
        from_attributes = True

# Pydantic model for returning receipt data (includes ID and uploaded_at)
class ReceiptOut(ReceiptCreate):
    id: int
    uploaded_at: datetime

# Pydantic model for updating receipt data (all fields are optional)
class ReceiptUpdate(BaseModel):
    vendor: Optional[str] = None
    transaction_date: Optional[datetime] = None
    amount: Optional[float] = None
    category: Optional[str] = None

