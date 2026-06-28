"""Normalize unit member gender values to canonical M/F codes."""

from typing import Optional


def normalize_member_gender(gender: Optional[str]) -> Optional[str]:
    """Map common gender inputs to canonical storage codes."""
    if gender is None:
        return None
    value = gender.strip()
    if not value:
        return None
    upper = value.upper()
    if upper in ("M", "MALE"):
        return "M"
    if upper in ("F", "FEMALE"):
        return "F"
    return value


def validate_member_gender(gender: Optional[str]) -> Optional[str]:
    """Normalize gender and reject values that are not M or F."""
    normalized = normalize_member_gender(gender)
    if normalized is None:
        return None
    if normalized not in ("M", "F"):
        raise ValueError("Gender must be Male or Female")
    return normalized
