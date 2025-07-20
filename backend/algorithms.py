# backend/algorithms.py

from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter
import math

# --- Search Algorithms ---

def linear_search_receipts(
    receipts: List[Dict[str, Any]],
    query: str,
    field: str,
    case_sensitive: bool = False
) -> List[Dict[str, Any]]:
    """
    Performs a linear search on a list of receipt dictionaries.
    Args:
        receipts: List of receipt dictionaries.
        query: The search query string.
        field: The field to search within (e.g., 'vendor', 'category', 'extracted_text').
        case_sensitive: If True, the search is case-sensitive.
    Returns:
        A list of matching receipt dictionaries.
    """
    results = []
    for receipt in receipts:
        field_value = str(receipt.get(field, "") or "") # Ensure it's a string, handle None
        if not case_sensitive:
            field_value = field_value.lower()
            query_lower = query.lower()
            if query_lower in field_value:
                results.append(receipt)
        else:
            if query in field_value:
                results.append(receipt)
    return results

def range_search_receipts_by_amount(
    receipts: List[Dict[str, Any]],
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Performs a range search on receipt amounts.
    Args:
        receipts: List of receipt dictionaries.
        min_amount: Minimum amount (inclusive).
        max_amount: Maximum amount (inclusive).
    Returns:
        A list of matching receipt dictionaries.
    """
    results = []
    for receipt in receipts:
        amount = receipt.get("amount")
        if amount is not None:
            if (min_amount is None or amount >= min_amount) and \
               (max_amount is None or amount <= max_amount):
                results.append(receipt)
    return results

def range_search_receipts_by_date(
    receipts: List[Dict[str, Any]],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Performs a range search on receipt transaction dates.
    Args:
        receipts: List of receipt dictionaries.
        start_date: Start date (inclusive).
        end_date: End date (inclusive).
    Returns:
        A list of matching receipt dictionaries.
    """
    results = []
    for receipt in receipts:
        tx_date = receipt.get("transaction_date")
        if tx_date is not None:
            if (start_date is None or tx_date >= start_date) and \
               (end_date is None or tx_date <= end_date):
                results.append(receipt)
    return results

# --- Sorting Algorithms ---

def sort_receipts(
    receipts: List[Dict[str, Any]],
    key: str,
    reverse: bool = False
) -> List[Dict[str, Any]]:
    """
    Sorts a list of receipt dictionaries using Python's Timsort algorithm.
    Args:
        receipts: List of receipt dictionaries.
        key: The field to sort by (e.g., 'amount', 'transaction_date', 'vendor').
        reverse: If True, sort in descending order.
    Returns:
        A new list of sorted receipt dictionaries.
    """
    # Timsort is efficient for various data distributions, O(n log n) average/worst case.
    return sorted(receipts, key=lambda x: x.get(key, 0) if isinstance(x.get(key), (int, float)) else str(x.get(key, '')), reverse=reverse)

# --- Aggregation Functions ---

def calculate_aggregates(receipts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates statistical aggregates for expenditure.
    Args:
        receipts: List of receipt dictionaries.
    Returns:
        A dictionary containing sum, mean, median, mode of expenditure,
        and frequency distribution of vendors.
    """
    if not receipts:
        return {
            "total_spend": 0.0,
            "mean_spend": 0.0,
            "median_spend": 0.0,
            "mode_spend": [],
            "vendor_frequency": {},
            "category_frequency": {}
        }

    amounts = [r.get("amount", 0.0) for r in receipts]
    vendors = [r.get("vendor", "Unknown") for r in receipts]
    categories = [r.get("category", "Unknown") for r in receipts]

    # Sum
    total_spend = sum(amounts)

    # Mean
    mean_spend = total_spend / len(amounts)

    # Median
    sorted_amounts = sorted(amounts)
    n = len(sorted_amounts)
    if n % 2 == 0:
        median_spend = (sorted_amounts[n // 2 - 1] + sorted_amounts[n // 2]) / 2
    else:
        median_spend = sorted_amounts[n // 2]

    # Mode
    amount_counts = Counter(amounts)
    max_count = 0
    if amount_counts: # Check if amount_counts is not empty
        max_count = max(amount_counts.values())
    mode_spend = [amount for amount, count in amount_counts.items() if count == max_count]

    # Vendor Frequency Distribution
    vendor_frequency = dict(Counter(vendors))

    # Category Frequency Distribution
    category_frequency = dict(Counter(categories))

    return {
        "total_spend": total_spend,
        "mean_spend": mean_spend,
        "median_spend": median_spend,
        "mode_spend": mode_spend,
        "vendor_frequency": vendor_frequency,
        "category_frequency": category_frequency
    }

def time_series_aggregation(receipts: List[Dict[str, Any]], period: str = "month") -> Dict[str, float]:
    """
    Aggregates expenditure over time (e.g., monthly).
    Args:
        receipts: List of receipt dictionaries.
        period: 'month' or 'year'.
    Returns:
        A dictionary with period (e.g., 'YYYY-MM') as key and total spend as value.
    """
    time_series_data = Counter()
    for receipt in receipts:
        tx_date = receipt.get("transaction_date")
        amount = receipt.get("amount", 0.0)
        if tx_date and isinstance(tx_date, datetime):
            if period == "month":
                key = tx_date.strftime("%Y-%m")
            elif period == "year":
                key = tx_date.strftime("%Y")
            else:
                raise ValueError("Period must be 'month' or 'year'")
            time_series_data[key] += amount
    return dict(sorted(time_series_data.items()))

