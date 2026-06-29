"""Tests for payment proof OCR amount parsing."""

from app.units.payment_ocr import parse_payment_amount_from_text


def test_parse_upi_receipt_text():
    text = """
790.00
Paid to
CSI Youth Movement Ktm
Banking name: CSI Youth Movement Ktm
28 June 2026, 8:37 pm
"""
    assert parse_payment_amount_from_text(text) == 790


def test_parse_rupees_prefix():
    assert parse_payment_amount_from_text("R790.00") == 790


def test_parse_ignores_date_line():
    text = "28 June 2026, 8:37 pm"
    assert parse_payment_amount_from_text(text) is None


def test_parse_engine1_misread_still_finds_largest_currency_like_value():
    text = "2790.00\nPaid to\nCSI Youth Movement Ktm"
    assert parse_payment_amount_from_text(text) == 2790
