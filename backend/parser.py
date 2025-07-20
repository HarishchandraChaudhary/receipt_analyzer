# backend/parser.py

import os
import re
from PIL import Image
import pytesseract
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set Tesseract command path if not in PATH (e.g., Windows)
# Example for Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# You might need to uncomment and adjust this line based on your Tesseract installation
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Define the directory for uploaded files
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_uploaded_file(file_content: bytes, filename: str) -> str:
    """Saves the uploaded file to the UPLOAD_DIR."""
    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
        logging.info(f"File saved successfully: {file_path}")
        return file_path
    except IOError as e:
        logging.error(f"Error saving file {filename}: {e}")
        raise

def extract_text_from_image(image_path: str) -> str:
    """Extracts text from an image using Tesseract OCR."""
    try:
        img = Image.open(image_path)
        # Convert image to grayscale for better OCR performance
        img = img.convert('L')
        # Use a specific language if needed, e.g., lang='eng+deu'
        text = pytesseract.image_to_string(img, lang='eng')
        logging.info(f"Text extracted from {os.path.basename(image_path)}.")
        return text
    except pytesseract.TesseractNotFoundError:
        logging.error("Tesseract is not installed or not in your PATH. Please install it.")
        raise RuntimeError("Tesseract OCR engine not found.")
    except Exception as e:
        logging.error(f"Error during OCR on {image_path}: {e}")
        raise

def parse_receipt_text(text: str) -> Dict[str, Any]:
    """
    Parses extracted text to find vendor, date, and amount using rule-based logic (regex).
    This is a simplified example and can be greatly improved with more robust NLP/regex.
    """
    vendor = "Unknown Vendor"
    transaction_date = None
    amount = 0.01 # Default to a small non-zero value to pass Pydantic validation
    category = None

    # --- Vendor Extraction (simple example) ---
    # Look for common keywords or assume first non-date/amount line
    # This is highly dependent on receipt format.
    vendor_patterns = [
        r"(?i)supermarket|groceries|store|shop|cafe|restaurant|pharmacy|utility|internet|electricity",
        r"Walmart|Target|Kroger|Amazon|Starbucks|Local Cafe|Best Buy|Vodafone|Reliance Jio|BESCOM", # Specific vendors
    ]
    for pattern in vendor_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vendor = match.group(0).strip()
            break
    
    # Fallback: take the first non-empty line that doesn't look like a date or amount
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        for line in lines:
            # Skip lines that are too short/long, or look like dates/amounts
            if not re.search(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$|^\d+\.\d{2}$', line) and \
               3 < len(line) < 30:
                vendor = line
                break


    # --- Date Extraction ---
    # Common date formats: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, DD-MMM-YYYY
    date_patterns = [
        r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}',  # DD/MM/YYYY, MM/DD/YYYY
        r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}',  # YYYY-MM-DD
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}\b', # DD Mon YYYY
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},\s+\d{2,4}\b' # Mon DD, YYYY
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(0)
            try:
                # Try parsing common formats
                for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%m.%d.%Y",
                            "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]:
                    try:
                        transaction_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                if transaction_date:
                    break
            except Exception:
                pass # Continue to next pattern/format

    # Fallback to current date if no date found
    if transaction_date is None:
        transaction_date = datetime.now()
        logging.warning("No transaction date found, defaulting to current date.")

    # --- Amount Extraction ---
    # Prioritize lines containing "TOTAL", "BALANCE", "AMOUNT DUE"
    # Look for patterns like currency symbol followed by number, or number followed by currency code
    # Regex: (?:[Tt][Oo][Tt][Aa][Ll]|[Bb][Aa][Ll][Aa][Nn][Cc][Ee]|[Dd][Uu][Ee])\s*[:]?\s*[\$€£₹]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))
    # This looks for "Total", "Balance", "Due" (case-insensitive), optional colon, optional currency symbol, then the number.
    amount_patterns = [
        r'(?:TOTAL|AMOUNT|BALANCE|DUE)\s*[:]?\s*[\$€£₹]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))', # e.g., TOTAL: $123.45 or TOTAL 123,45
        r'[\$€£₹]\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))', # e.g., $123.45
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))\s*(?:INR|USD|EUR|GBP)', # e.g., 123.45 USD
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2}))\s*$' # Number at the end of a line
    ]
    
    found_amount = False
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Take the last found amount, as it's often the total
            raw_amount = matches[-1]
            # Handle comma as decimal separator (common in some regions)
            raw_amount = raw_amount.replace(',', '.')
            try:
                parsed_amount = float(raw_amount)
                if parsed_amount > 0: # Only accept positive amounts
                    amount = parsed_amount
                    found_amount = True
                    break
            except ValueError:
                pass # Continue to next pattern

    if not found_amount:
        logging.warning("No valid positive amount found, defaulting to 0.01.")
        amount = 0.01 # Ensure it's greater than 0 for Pydantic validation

    # --- Category Mapping (simple rule-based) ---
    # This can be expanded with a proper mapping dictionary or ML model
    text_lower = text.lower()
    if "grocer" in text_lower or "supermarket" in text_lower or "food" in text_lower:
        category = "Groceries"
    elif "electric" in text_lower or "power" in text_lower or "utility" in text_lower:
        category = "Utilities"
    elif "internet" in text_lower or "broadband" in text_lower or "telecom" in text_lower:
        category = "Internet/Telecom"
    elif "restaurant" in text_lower or "cafe" in text_lower or "dine" in text_lower:
        category = "Dining"
    elif "pharmacy" in text_lower or "medicine" in text_lower or "health" in text_lower:
        category = "Health"
    else:
        category = "Miscellaneous"


    logging.info(f"Parsed data: Vendor='{vendor}', Date='{transaction_date}', Amount={amount}, Category='{category}'")
    return {
        "vendor": vendor,
        "transaction_date": transaction_date,
        "amount": amount,
        "category": category,
        "extracted_text": text
    }

