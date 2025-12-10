import re


def extract_vendor(text: str):
    """
    Extracts the vendor/company name.

    Strategy:
    - Find 'Sold By:' (or similar)
    - Take the first non-empty line after it that doesn't look like an address label.
    """
    # Normalize line endings
    lines = text.splitlines()

    for i, line in enumerate(lines):
        if "sold by" in line.lower():
            # Look at following lines to find the actual name
            for j in range(i + 1, min(i + 5, len(lines))):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                # Skip obvious labels
                lower_cand = candidate.lower()
                if "billing address" in lower_cand or "shipping address" in lower_cand:
                    continue
                # This is likely the vendor name
                return candidate

    # Fallback: try generic patterns
    patterns = [
        r"Vendor[:\s]+(.+)",
        r"Supplier[:\s]+(.+)",
        r"Company Name[:\s]+(.+)",
        r"Bill From[:\s]+(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            line = match.group(1).strip()
            return line.split("\n")[0].strip()

    # Final fallback: first non-empty line
    for line in lines:
        line = line.strip()
        if line:
            return line
    return None


def extract_invoice_number(text: str):
    """
    Extracts invoice number from text.
    """
    patterns = [
        r"Invoice Number[:\s]+([\w-]+)",
        r"Invoice No[:\s]+([\w-]+)",
        r"Inv\.\s*No[:\s]+([\w-]+)",
        r"Invoice #[:\s]+([\w-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def extract_invoice_date(text: str):
    """
    Extracts date in formats like:
    24.09.2025, 24/09/2025, 24-09-2025, etc.
    Prioritises 'Invoice Date' label if present.
    """
    # Prefer the explicit "Invoice Date" label
    labeled_pattern = r"Invoice Date[:\s]+(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"
    match = re.search(labeled_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: any date-like pattern
    generic_pattern = r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})"
    match = re.search(generic_pattern, text)
    return match.group(1).strip() if match else None


import re

import re

def _to_float(num_str: str):
    """
    Convert '16,134.56' or '1799.00' -> float.
    Ignores clearly non-amount values (too many digits before decimal).
    """
    try:
        cleaned = num_str.replace(",", "")
        if cleaned.strip() == "" or cleaned.strip() == ".":
            return None

        whole = cleaned.split(".")[0]
        # Allow up to 6 digits before decimal (<= 999,999.xx)
        # Anything longer is probably an order id / phone / OCR garbage.
        if len(whole) > 6:
            return None

        return float(cleaned)
    except ValueError:
        return None


def extract_total_amount(text: str):
    """
    Extract the total invoice amount.

    Strategy:
    1. Prefer lines with labels like:
       'TOTAL PAY', 'GRAND TOTAL', 'TOTAL PRICE', 'Total amount', etc.
    2. If no labeled total is found, scan all money-like decimals and
       pick the largest realistic one (using _to_float).
    """

    # 1️⃣ Label-based patterns (high priority)
    #   Matches:  'TOTAL PAY   $11,495.04'
    #             'GRAND TOTAL : 1856.06'
    #             'Total amount  16,134.56'
    labeled_pattern = re.compile(
        r"(TOTAL PAY|TOTAL PRICE|GRAND TOTAL|Total Amount|Total amount|Amount Payable|Invoice Total)"
        r"[^\d]*([\$₹]?\s*[\d,]+\.\d{2})",
        re.IGNORECASE
    )

    labeled_matches = labeled_pattern.findall(text)
    if labeled_matches:
        # Each match is (label, value); we pick the numerically largest value
        candidates = []
        for label, val in labeled_matches:
            val = val.replace("₹", "").replace("$", "").strip()
            num = _to_float(val)
            if num is not None:
                candidates.append((val, num))

        if candidates:
            best_str, _ = max(candidates, key=lambda x: x[1])
            return best_str

    # 2️⃣ Generic fallback – collect all decimal numbers like 16,134.56 / 1799.00
    all_numbers = re.findall(r"\d[\d,]*\.\d{2}", text)
    if not all_numbers:
        return None

    numeric_values = []
    for num_str in all_numbers:
        val = _to_float(num_str)
        if val is not None:
            numeric_values.append((num_str, val))

    if not numeric_values:
        return None

    # Pick the largest realistic amount
    best_str, _ = max(numeric_values, key=lambda x: x[1])
    return best_str




def extract_fields(text: str):
    """
    Extract all invoice fields and return a dictionary.
    """
    return {
        "Vendor": extract_vendor(text),
        "Invoice Number": extract_invoice_number(text),
        "Invoice Date": extract_invoice_date(text),
        "Total Amount": extract_total_amount(text),
    }
