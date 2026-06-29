"""Phone number parsing, validation, and normalization utilities."""

from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

DEFAULT_REGION = "IN"


class InvalidPhoneError(ValueError):
    """Raised when a phone number cannot be parsed or validated."""


def normalize_phone(value: str | None, default_region: str = DEFAULT_REGION) -> str | None:
    """Return a valid phone number in E.164 format, or None for empty input."""
    if value is None:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None

    parse_attempts: list[str | None] = []
    if trimmed.startswith("+"):
        parse_attempts.append(None)
    parse_attempts.append(default_region)

    for region in parse_attempts:
        try:
            parsed = phonenumbers.parse(trimmed, region)
        except NumberParseException:
            continue

        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

    raise InvalidPhoneError("Invalid phone number")


def validate_and_normalize_phone(value: str, default_region: str = DEFAULT_REGION) -> str:
    """Validate and normalize a required phone number to E.164."""
    normalized = normalize_phone(value, default_region=default_region)
    if normalized is None:
        raise InvalidPhoneError("Phone number is required")
    return normalized


def normalize_optional_phone(value: str | None, default_region: str = DEFAULT_REGION) -> str | None:
    """Validate and normalize an optional phone number to E.164."""
    if value is None:
        return None
    return validate_and_normalize_phone(value, default_region=default_region)


def phone_lookup_variants(value: str, default_region: str = DEFAULT_REGION) -> list[str]:
    """Return equivalent phone formats for legacy database lookups."""
    trimmed = value.strip()
    if not trimmed:
        return []

    variants: set[str] = {trimmed}

    try:
        normalized = normalize_phone(trimmed, default_region=default_region)
    except InvalidPhoneError:
        normalized = None

    if normalized:
        variants.add(normalized)
        if normalized.startswith("+91"):
            variants.add(normalized[3:])

    if trimmed.isdigit() and len(trimmed) == 10:
        variants.add(f"+91{trimmed}")

    return list(variants)


def normalize_member_phone(value: str, residence_location: str | None = None) -> str:
    """Normalize member phone numbers, allowing international numbers when outside India."""
    if residence_location == "OUTSIDE_INDIA" and value.strip().startswith("+"):
        return validate_and_normalize_phone(value, default_region=DEFAULT_REGION)
    return validate_and_normalize_phone(value, default_region=DEFAULT_REGION)
