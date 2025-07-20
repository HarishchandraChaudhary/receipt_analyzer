# backend/main.py

import os
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime

# Import models, database functions, and parsing/algorithm logic
from . import models, database, parser, algorithms

# Create FastAPI app instance
app = FastAPI(
    title="Receipt Analyzer API",
    description="API for uploading, parsing, storing, and analyzing receipts.",
    version="1.0.0"
)

# Ensure the database and tables are created on startup
database.create_db_and_tables()

# Mount the 'uploads' directory to serve static files (uploaded receipts)
# This allows the frontend to access the uploaded images directly
app.mount("/uploads", StaticFiles(directory=parser.UPLOAD_DIR), name="uploads")

# Dependency to get a database session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Welcome to the Receipt Analyzer API! Visit /docs for API documentation."}

@app.post("/upload-receipt/", response_model=models.ReceiptOut)
async def upload_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Uploads a receipt file, extracts text using OCR, parses data, and stores it.
    Supports .jpg, .png, .pdf, .txt.
    """
    # Validate file type
    allowed_content_types = ["image/jpeg", "image/png", "application/pdf", "text/plain"]
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed types: {', '.join(allowed_content_types)}"
        )

    # Read file content
    file_content = await file.read()
    filename = file.filename

    # Save the file
    try:
        file_path = parser.save_uploaded_file(file_content, filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Extract text based on file type
    extracted_text = ""
    if file.content_type.startswith("image/"):
        try:
            extracted_text = parser.extract_text_from_image(file_path)
        except Exception as e:
            # Clean up the partially saved file if OCR fails
            os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"OCR failed for image: {e}")
    elif file.content_type == "text/plain":
        extracted_text = file_content.decode('utf-8')
    elif file.content_type == "application/pdf":
        # Basic PDF handling: For simplicity, this example doesn't include PDF OCR.
        # You would need a library like `pdfminer.six` or `PyPDF2` to extract text
        # or convert PDF to images for OCR.
        # For this assignment, we'll just store a placeholder text for PDF.
        extracted_text = f"Text extraction for PDF not implemented in this demo. File: {filename}"
        print("Warning: PDF text extraction not fully implemented in this demo.")
        # If you want to implement PDF OCR, you'd convert each page to an image and then OCR
        # from pdf2image import convert_from_path
        # images = convert_from_path(file_path)
        # for i, image in enumerate(images):
        #     extracted_text += pytesseract.image_to_string(image) + "\n"


    # Parse extracted data
    try:
        parsed_data = parser.parse_receipt_text(extracted_text)
    except Exception as e:
        # Clean up the partially saved file if parsing fails
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to parse extracted text: {e}")

    # Create a ReceiptCreate Pydantic model instance for validation
    try:
        receipt_data = models.ReceiptCreate(
            filename=filename,
            vendor=parsed_data.get("vendor", "Unknown Vendor"),
            transaction_date=parsed_data.get("transaction_date", datetime.now()),
            amount=parsed_data.get("amount", 0.0),
            category=parsed_data.get("category", "Miscellaneous"),
            extracted_text=extracted_text
        )
    except Exception as e:
        # Clean up the partially saved file if Pydantic validation fails
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=f"Data validation failed: {e}")

    # Store in database
    db_receipt = database.Receipt(**receipt_data.model_dump())
    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)

    return db_receipt

@app.get("/receipts/", response_model=List[models.ReceiptOut])
async def get_all_receipts(db: Session = Depends(get_db)):
    """Retrieves all stored receipts."""
    receipts = db.query(database.Receipt).all()
    return receipts

@app.get("/receipts/{receipt_id}", response_model=models.ReceiptOut)
async def get_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Retrieves a single receipt by its ID."""
    receipt = db.query(database.Receipt).filter(database.Receipt.id == receipt_id).first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt

@app.put("/receipts/{receipt_id}", response_model=models.ReceiptOut)
async def update_receipt(
    receipt_id: int,
    receipt_update: models.ReceiptUpdate,
    db: Session = Depends(get_db)
):
    """Updates an existing receipt's fields."""
    db_receipt = db.query(database.Receipt).filter(database.Receipt.id == receipt_id).first()
    if db_receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")

    update_data = receipt_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_receipt, key, value)

    db.add(db_receipt)
    db.commit()
    db.refresh(db_receipt)
    return db_receipt

@app.delete("/receipts/{receipt_id}", status_code=204)
async def delete_receipt(receipt_id: int, db: Session = Depends(get_db)):
    """Deletes a receipt by its ID, and its associated file."""
    db_receipt = db.query(database.Receipt).filter(database.Receipt.id == receipt_id).first()
    if db_receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Delete the associated file from the uploads directory
    file_path = os.path.join(parser.UPLOAD_DIR, db_receipt.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            # Do not raise HTTPException, just log the error, as DB delete is more critical

    db.delete(db_receipt)
    db.commit()
    return {"message": "Receipt deleted successfully"}

@app.get("/receipts/{receipt_id}/file")
async def get_receipt_file(receipt_id: int, db: Session = Depends(get_db)):
    """Serves the uploaded receipt file."""
    db_receipt = db.query(database.Receipt).filter(database.Receipt.id == receipt_id).first()
    if db_receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")

    file_path = os.path.join(parser.UPLOAD_DIR, db_receipt.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(path=file_path, filename=db_receipt.filename, media_type="application/octet-stream")


@app.get("/search-receipts/", response_model=List[models.ReceiptOut])
async def search_receipts(
    query: Optional[str] = None,
    field: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Searches receipts based on keyword, amount range, or date range.
    """
    all_receipts = db.query(database.Receipt).all()
    receipts_as_dicts = [r.__dict__ for r in all_receipts] # Convert ORM objects to dicts for algorithms

    filtered_receipts = receipts_as_dicts

    # Apply keyword search
    if query and field:
        if field not in ["vendor", "category", "extracted_text", "filename"]:
            raise HTTPException(status_code=400, detail="Invalid search field.")
        filtered_receipts = algorithms.linear_search_receipts(filtered_receipts, query, field)

    # Apply amount range search
    if min_amount is not None or max_amount is not None:
        filtered_receipts = algorithms.range_search_receipts_by_amount(filtered_receipts, min_amount, max_amount)

    # Apply date range search
    if start_date is not None or end_date is not None:
        filtered_receipts = algorithms.range_search_receipts_by_date(filtered_receipts, start_date, end_date)

    # Convert back to Pydantic model for response
    return [models.ReceiptOut(**r) for r in filtered_receipts]


@app.get("/sort-receipts/", response_model=List[models.ReceiptOut])
async def sort_receipts_endpoint(
    sort_by: str = "transaction_date",
    order: str = "desc", # 'asc' or 'desc'
    db: Session = Depends(get_db)
):
    """
    Sorts receipts by a specified field.
    """
    if sort_by not in ["vendor", "transaction_date", "amount", "category", "uploaded_at"]:
        raise HTTPException(status_code=400, detail="Invalid sort_by field.")
    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid order. Must be 'asc' or 'desc'.")

    all_receipts = db.query(database.Receipt).all()
    receipts_as_dicts = [r.__dict__ for r in all_receipts]

    reverse_sort = True if order == "desc" else False
    sorted_receipts = algorithms.sort_receipts(receipts_as_dicts, sort_by, reverse_sort)

    return [models.ReceiptOut(**r) for r in sorted_receipts]


@app.get("/insights/", response_model=Dict[str, Any])
async def get_insights(db: Session = Depends(get_db)):
    """
    Provides summarized insights such as total spend, top vendors, and billing trends.
    """
    all_receipts = db.query(database.Receipt).all()
    receipts_as_dicts = [r.__dict__ for r in all_receipts]

    # Calculate basic aggregates
    basic_aggregates = algorithms.calculate_aggregates(receipts_as_dicts)

    # Calculate time-series aggregates
    monthly_spend_trend = algorithms.time_series_aggregation(receipts_as_dicts, period="month")
    yearly_spend_trend = algorithms.time_series_aggregation(receipts_as_dicts, period="year")

    # Get top vendors (e.g., top 5)
    vendor_frequency = basic_aggregates.get("vendor_frequency", {})
    sorted_vendors = sorted(vendor_frequency.items(), key=lambda item: item[1], reverse=True)
    top_vendors = sorted_vendors[:5] # Get top 5 vendors

    # Get category distribution
    category_distribution = basic_aggregates.get("category_frequency", {})

    return {
        "total_spend": basic_aggregates["total_spend"],
        "mean_spend": basic_aggregates["mean_spend"],
        "median_spend": basic_aggregates["median_spend"],
        "mode_spend": basic_aggregates["mode_spend"],
        "top_vendors": top_vendors,
        "category_distribution": category_distribution,
        "monthly_spend_trend": monthly_spend_trend,
        "yearly_spend_trend": yearly_spend_trend
    }

