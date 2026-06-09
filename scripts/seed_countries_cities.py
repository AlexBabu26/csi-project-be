"""Deprecated: use scripts/seed_location_master.py for hierarchical country-state-city seeding."""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.auth.models  # noqa: F401
import app.units.models  # noqa: F401

from sqlalchemy import delete, func, select

from app.auth.models import City, Country
from app.common.db import session_scope

COUNTRIES_URL = (
    "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/"
    "master/json/countries.json"
)
COUNTRIES_CITIES_URL = (
    "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/"
    "master/json/countries+cities.json"
)
BATCH_SIZE = 2000


def _download_json(url: str) -> list[dict]:
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url, timeout=180) as response:
        return json.load(response)


def seed_countries_cities(*, force: bool = False) -> None:
    with session_scope() as db:
        existing_countries = db.scalar(select(func.count()).select_from(Country)) or 0
        existing_cities = db.scalar(select(func.count()).select_from(City)) or 0

        if existing_countries and existing_cities and not force:
            print(
                f"Skipping seed: {existing_countries} countries and {existing_cities} cities already present."
            )
            return

        if force and (existing_countries or existing_cities):
            print("Force mode enabled: clearing existing city/country data.")
            db.execute(delete(City))
            db.execute(delete(Country))
            db.flush()
            existing_countries = 0

        country_by_name: dict[str, int] = {}

        if not existing_countries:
            countries_data = _download_json(COUNTRIES_URL)
            for row in countries_data:
                country = Country(
                    name=row["name"],
                    iso_code=(row.get("iso2") or "").upper() or None,
                )
                db.add(country)
                db.flush()
                country_by_name[country.name.lower()] = country.id
            print(f"Inserted {len(country_by_name)} countries.")
        else:
            countries = db.scalars(select(Country)).all()
            country_by_name = {country.name.lower(): country.id for country in countries}
            print(f"Using {len(country_by_name)} existing countries.")

        if existing_cities and not force:
            print(f"Skipping city seed: {existing_cities} cities already present.")
            return

        countries_cities_data = _download_json(COUNTRIES_CITIES_URL)
        pending_cities: list[City] = []
        inserted = 0

        for row in countries_cities_data:
            country_id = country_by_name.get((row.get("name") or "").lower())
            if not country_id:
                continue

            seen_city_names: set[str] = set()
            for city_row in row.get("cities") or []:
                city_name = city_row.get("name") if isinstance(city_row, dict) else city_row
                if not city_name:
                    continue

                dedupe_key = city_name.strip().lower()
                if dedupe_key in seen_city_names:
                    continue
                seen_city_names.add(dedupe_key)

                pending_cities.append(
                    City(
                        country_id=country_id,
                        name=city_name.strip(),
                    )
                )
                inserted += 1

                if len(pending_cities) >= BATCH_SIZE:
                    db.add_all(pending_cities)
                    db.flush()
                    pending_cities.clear()

        if pending_cities:
            db.add_all(pending_cities)
            db.flush()

        city_count = db.scalar(select(func.count()).select_from(City)) or 0
        print(f"Inserted {city_count} cities.")


if __name__ == "__main__":
    force_seed = "--force" in sys.argv
    seed_countries_cities(force=force_seed)
