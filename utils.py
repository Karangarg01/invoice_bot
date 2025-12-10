import logging
import os
from typing import Dict, Tuple


LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "invoice_bot.log")


def get_logger(name: str = "invoice_bot") -> logging.Logger:
    """
    Returns a configured logger that writes to logs/invoice_bot.log
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def validate_record(record: Dict) -> Tuple[str, str]:
    """
    Basic validation for an extracted invoice record.
    Returns (status, comment).
    Status: 'OK', 'WARNING', or 'ERROR'
    """
    missing = [k for k, v in record.items() if k != "Filename" and not v]

    if "Total Amount" not in record or not record["Total Amount"]:
        return "ERROR", "Missing total amount."

    if missing:
        return "WARNING", f"Missing fields: {', '.join(missing)}"

    return "OK", "All key fields present."
