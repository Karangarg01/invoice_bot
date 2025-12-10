import os
from pdf2image import convert_from_path
import pytesseract
import pandas as pd
from utils import get_logger, validate_record

from invoice_parser import extract_fields

INVOICE_DIR = "invoices"
TEXT_OUTPUT_DIR = "extracted_text"
OUTPUT_DIR = "output"

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = None


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Convert PDF to images and extract text using Tesseract OCR.
    Returns the extracted text as a single string.
    """
    print(f"Processing: {pdf_path}")

    # Use poppler_path only if explicitly set
    if POPPLER_PATH:
        pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    else:
        pages = convert_from_path(pdf_path)

    full_text = ""

    for page_number, page in enumerate(pages, start=1):
        print(f"   ➜ Running OCR on page {page_number}...")
        text = pytesseract.image_to_string(page)
        full_text += f"\n\n================ Page {page_number} ================\n\n"
        full_text += text

    return full_text


def save_raw_text(filename: str, text: str):
    """
    Save extracted raw text to the extracted_text/ folder as a .txt file.
    """
    os.makedirs(TEXT_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(TEXT_OUTPUT_DIR, f"{filename}.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Saved extracted text to: {output_path}")


def main():
    logger = get_logger()

    # Ensure invoice folder exists
    if not os.path.exists(INVOICE_DIR):
        print(f"Folder '{INVOICE_DIR}' not found.")
        return

    pdf_files = [f for f in os.listdir(INVOICE_DIR) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"No PDF files found in '{INVOICE_DIR}'. Add at least one PDF invoice.")
        return

    records = []

    for pdf_file in pdf_files:
        pdf_path = os.path.join(INVOICE_DIR, pdf_file)
        text = extract_text_from_pdf(pdf_path)
        base_name = os.path.splitext(pdf_file)[0]
        save_raw_text(base_name, text)
        fields = extract_fields(text)

        record = {
            "Filename": base_name,
            "Vendor": fields.get("Vendor"),
            "Invoice Number": fields.get("Invoice Number"),
            "Invoice Date": fields.get("Invoice Date"),
            "Total Amount": fields.get("Total Amount"),
        }
        status, comment = validate_record(record)
        record["Status"] = status
        record["Comments"] = comment
        logger.info(f"{base_name} - {status} - {comment}")
        records.append(record)
    if records:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df = pd.DataFrame(records)
        output_file = os.path.join(OUTPUT_DIR, "invoice_data.xlsx")
        df.to_excel(output_file, index=False)
        print(f"Structured data saved to: {output_file}")
    else:
        print("No records to save. Check if parsing logic is working correctly.")

    print("All PDFs processed successfully!")


if __name__ == "__main__":
    main()
