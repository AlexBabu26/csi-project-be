"""Shared helpers for serializing unit member fields including residence."""

from typing import Any

from sqlalchemy.orm import selectinload

from app.auth.models import City, ResidenceLocation, State, UnitMembers

RESIDENCE_LOCATION_LABELS = {
    ResidenceLocation.WITHIN_KERALA: "Lives in Kerala",
    ResidenceLocation.OUTSIDE_KERALA: "Outside Kerala (India)",
    ResidenceLocation.OUTSIDE_INDIA: "Outside India",
}

MEMBER_RESIDENCE_LOAD_OPTIONS = (
    selectinload(UnitMembers.residence_state).selectinload(State.country),
    selectinload(UnitMembers.residence_city).selectinload(City.country),
    selectinload(UnitMembers.residence_city).selectinload(City.state),
)


def format_member_residence_label(member: UnitMembers) -> str:
    if not member.residence_location:
        return "Not set"
    if member.residence_location == ResidenceLocation.WITHIN_KERALA:
        if member.residence_state_name and member.residence_country_name:
            return f"{member.residence_state_name}, {member.residence_country_name}"
        return "Lives in Kerala"
    if member.residence_state_name and member.residence_country_name:
        if member.residence_city_name:
            return (
                f"{member.residence_city_name}, "
                f"{member.residence_state_name}, "
                f"{member.residence_country_name}"
            )
        return f"{member.residence_state_name}, {member.residence_country_name}"
    return RESIDENCE_LOCATION_LABELS.get(member.residence_location, "Not set")


def member_residence_fields(member: UnitMembers) -> dict[str, Any]:
    return {
        "residence_location": (
            member.residence_location.value if member.residence_location else None
        ),
        "residence_state_id": member.residence_state_id,
        "residence_city_id": member.residence_city_id,
        "residence_state_name": member.residence_state_name,
        "residence_city_name": member.residence_city_name,
        "residence_country_name": member.residence_country_name,
        "residence_country_id": member.residence_country_id,
        "residence_label": format_member_residence_label(member),
    }


def member_base_fields(member: UnitMembers) -> dict[str, Any]:
    return {
        "id": member.id,
        "registered_user_id": member.registered_user_id,
        "name": member.name,
        "gender": member.gender,
        "dob": member.dob.isoformat() if member.dob else None,
        "age": member.age,
        "number": member.number,
        "qualification": member.qualification,
        "blood_group": member.blood_group,
    }


def serialize_member(member: UnitMembers) -> dict[str, Any]:
    return {**member_base_fields(member), **member_residence_fields(member)}


def member_export_row(member: UnitMembers, *, unit_name: str = "", district: str = "") -> dict[str, Any]:
    row = serialize_member(member)
    row["unit_name"] = unit_name
    row["district"] = district
    return row
