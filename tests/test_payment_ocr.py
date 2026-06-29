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


def test_parse_dark_mode_rupee_misread_as_leading_two():
    text = """
2820.00
Paid to
CSI Youth Movement Ktm
27 June 2024, 7:55 pm
"""
    assert parse_payment_amount_from_text(text) == 820


def test_parse_keeps_four_digit_payment():
    text = """
2500.00
Paid to
Merchant Name
"""
    assert parse_payment_amount_from_text(text) == 2500


def test_parse_stops_at_paid_to_and_ignores_later_numbers():
    text = """
820.00
Paid to
CSI Youth Movement
27 June 2024, 7:55 pm
"""
    assert parse_payment_amount_from_text(text) == 820
