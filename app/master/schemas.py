"""Schemas for country/city master data."""

from pydantic import BaseModel, ConfigDict


class CountryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iso_code: str | None = None


class StateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country_id: int
    name: str


class StateSummaryResponse(BaseModel):
    id: int
    country_id: int
    name: str
    city_count: int
    city_required: bool


class CityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    country_id: int
    state_id: int | None = None
    name: str
