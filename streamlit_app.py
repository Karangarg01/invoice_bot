import os
import tempfile
from io import BytesIO

import streamlit as st
import pandas as pd

from pdf2image import convert_from_path
import pytesseract

from invoice_parser import extract_fields
from utils import validate_record

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

POPPLER_PATH = None


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Convert PDF to images and extract text using Tesseract OCR.
    Returns the extracted text as a single string.
    """
    if POPPLER_PATH:
        pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    else:
        pages = convert_from_path(pdf_path)

    full_text = ""

    for page_number, page in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page)
        full_text += f"\n\n================ Page {page_number} ================\n\n"
        full_text += text

    return full_text


def build_excel_download(df: pd.DataFrame) -> bytes:
    """
    Create an Excel file in memory from a DataFrame and
    return its binary content.
    """
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Invoices")
    buffer.seek(0)
    return buffer.getvalue()


def main():
    st.set_page_config(page_title="Invoice Bot UI", layout="wide")

    st.title("Invoice Bot – OCR Invoice Extractor")
    st.write(
        "Upload one or more PDF invoices (Amazon, Flipkart, etc.) and this app will "
        "run OCR, extract key fields, and show the results in a table."
    )

    uploaded_files = st.file_uploader(
        "Upload invoice PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        help="You can select multiple files at once."
    )

    if not uploaded_files:
        st.info("Upload at least one PDF to begin.")
        return

    if st.button("Process Invoices"):
        records = []

        progress = st.progress(0)
        status_text = st.empty()

        total_files = len(uploaded_files)

        for idx, uploaded_file in enumerate(uploaded_files, start=1):
            status_text.write(f"Processing: **{uploaded_file.name}** ({idx}/{total_files})")

            # Save uploaded file to a temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                temp_pdf_path = tmp_file.name


            try:
                text = extract_text_from_pdf(temp_pdf_path)
            except Exception as e:
                record = {
                    "Filename": uploaded_file.name,
                    "Vendor": None,
                    "Invoice Number": None,
                    "Invoice Date": None,
                    "Total Amount": None,
                    "Status": "ERROR",
                    "Comments": f"OCR failed: {e}",
                }
                records.append(record)
                os.unlink(temp_pdf_path)
                progress.progress(idx / total_files)
                continue

            fields = extract_fields(text)

            record = {
                "Filename": uploaded_file.name,
                "Vendor": fields.get("Vendor"),
                "Invoice Number": fields.get("Invoice Number"),
                "Invoice Date": fields.get("Invoice Date"),
                "Total Amount": fields.get("Total Amount"),
            }

            status, comment = validate_record(record)
            record["Status"] = status
            record["Comments"] = comment

            records.append(record)

            os.unlink(temp_pdf_path)

            progress.progress(idx / total_files)

        status_text.write("Processing completed.")

        if not records:
            st.error("No records were generated. Check your invoices or logs.")
            return

        df = pd.DataFrame(records)

        st.subheader("Extracted Invoice Data")
        st.dataframe(df, use_container_width=True)

        st.markdown("### Summary by Status")
        st.write(df["Status"].value_counts())

        excel_bytes = build_excel_download(df)
        st.download_button(
            label="Download as Excel",
            data=excel_bytes,
            file_name="invoice_data_streamlit.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


if __name__ == "__main__":
    main()
