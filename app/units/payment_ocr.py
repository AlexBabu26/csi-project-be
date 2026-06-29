"""Payment proof OCR helpers (OCR.space fallback for PDFs)."""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.common.config import get_settings

logger = logging.getLogger(__name__)

OCR_SPACE_URL = "https://api.ocr.space/parse/image"

AMOUNT_PATTERN = re.compile(
    r"(?:₹|Rs\.?|INR|[R₹])?\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}\s+\w+\s+\d{4})\b",
    re.IGNORECASE,
)
PAID_TO_PATTERN = re.compile(r"^paid\s+to\b", re.IGNORECASE)


def _correct_rupee_misread_amount(compact: str, value: float) -> float:
    match = re.match(r"^2([789]\d{2}\.\d{2})$", compact)
    if not match:
        return value

    try:
        return float(match.group(1))
    except ValueError:
        return value


def _parse_amount_from_line(trimmed: str) -> Optional[float]:
    if not trimmed or DATE_PATTERN.search(trimmed) or PAID_TO_PATTERN.match(trimmed):
        return None

    compact = re.sub(r"\s+", "", trimmed)
    match = AMOUNT_PATTERN.search(compact)
    if not match:
        return None

    raw = match.group(1).replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return None

    if value < 1:
        return None

    has_decimal = "." in match.group(1)
    looks_like_currency = (
        has_decimal
        or compact.startswith(("₹", "R"))
        or trimmed.lower().startswith("rs")
    )
    if not looks_like_currency:
        return None

    return _correct_rupee_misread_amount(compact, value)


def parse_payment_amount_from_text(text: str) -> Optional[int]:
    """Extract the most likely paid amount (whole rupees) from OCR text."""
    if not text or not text.strip():
        return None

    lines = text.splitlines()
    before_paid_to: list[str] = []

    for line in lines:
        trimmed = line.strip()
        if PAID_TO_PATTERN.match(trimmed):
            break
        if trimmed:
            before_paid_to.append(trimmed)

    search_lines = before_paid_to or [line.strip() for line in lines if line.strip()]

    for line in search_lines:
        parsed = _parse_amount_from_line(line)
        if parsed is not None and re.search(r"\.\d{1,2}", re.sub(r"\s+", "", line)):
            return int(round(parsed))

    for line in search_lines:
        parsed = _parse_amount_from_line(line)
        if parsed is not None:
            return int(round(parsed))

    return None


def extract_amount_from_pdf_bytes(
    file_bytes: bytes,
    filename: str,
) -> Optional[int]:
    """
    Run OCR.space on a PDF (or image) and return detected paid amount in rupees.
    Returns None when API key is missing, request fails, or no amount is found.
    """
    settings = get_settings()
    api_key = (settings.ocr_space_api_key or "").strip()
    if not api_key:
        logger.info("OCR.space API key not configured; skipping PDF amount detection")
        return None

    if len(file_bytes) > 1024 * 1024:
        logger.warning(
            "PDF exceeds OCR.space free-tier 1MB limit (%s bytes); skipping OCR",
            len(file_bytes),
        )
        return None

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                OCR_SPACE_URL,
                headers={"apikey": api_key},
                data={
                    "language": "eng",
                    "OCREngine": "2",
                    "scale": "true",
                    "isTable": "true",
                },
                files={
                    "file": (
                        filename or "payment.pdf",
                        file_bytes,
                        "application/pdf",
                    ),
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("OCR.space request failed: %s", exc)
        return None

    if payload.get("IsErroredOnProcessing"):
        logger.warning(
            "OCR.space processing error: %s",
            payload.get("ErrorMessage") or payload.get("ErrorDetails"),
        )
        return None

    parsed_results = payload.get("ParsedResults") or []
    if not parsed_results:
        return None

    combined_text = "\n".join(
        result.get("ParsedText") or "" for result in parsed_results if result.get("ParsedText")
    )
    return parse_payment_amount_from_text(combined_text)
