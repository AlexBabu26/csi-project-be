"""Seed country, state, and city master tables with proper FK hierarchy."""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.auth.models  # noqa: F401
import app.units.models  # noqa: F401

from sqlalchemy import delete, func, select, update

from app.auth.models import City, Country, State, UnitMembers
from app.common.db import session_scope

HIERARCHY_URL = (
    "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/"
    "master/json/countries+states+cities.json"
)
BATCH_SIZE = 2000


def _download_json(url: str) -> list[dict]:
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url, timeout=300) as response:
        return json.load(response)


def _flush_batch(db, pending: list) -> None:
    if not pending:
        return
    db.add_all(pending)
    db.flush()
    pending.clear()


def seed_location_master(*, force: bool = False) -> None:
    with session_scope() as db:
        existing_countries = db.scalar(select(func.count()).select_from(Country)) or 0
        existing_states = db.scalar(select(func.count()).select_from(State)) or 0
        existing_cities = db.scalar(select(func.count()).select_from(City)) or 0

        if existing_countries and existing_states and existing_cities and not force:
            print(
                "Skipping seed: "
                f"{existing_countries} countries, {existing_states} states, {existing_cities} cities already present."
            )
            return

        if force and (existing_countries or existing_states or existing_cities):
            print("Force mode enabled: clearing member residence FKs and master location data.")
            db.execute(
                update(UnitMembers).values(
                    residence_location=None,
                    residence_state_id=None,
                    residence_city_id=None,
                )
            )
            db.execute(delete(City))
            db.execute(delete(State))
            db.execute(delete(Country))
            db.flush()

        hierarchy_data = _download_json(HIERARCHY_URL)

        country_by_name: dict[str, int] = {}
        pending_countries: list[Country] = []
        for row in hierarchy_data:
            country = Country(
                name=row["name"],
                iso_code=(row.get("iso2") or "").upper() or None,
            )
            pending_countries.append(country)
        db.add_all(pending_countries)
        db.flush()
        for country in pending_countries:
            country_by_name[country.name.lower()] = country.id
        print(f"Inserted {len(country_by_name)} countries.")

        pending_states: list[State] = []
        state_count = 0
        for row in hierarchy_data:
            country_id = country_by_name.get((row.get("name") or "").lower())
            if not country_id:
                continue

            seen_state_names: set[str] = set()
            for state_row in row.get("states") or []:
                state_name = state_row.get("name") if isinstance(state_row, dict) else state_row
                if not state_name:
                    continue

                dedupe_key = str(state_name).strip().lower()
                if dedupe_key in seen_state_names:
                    continue
                seen_state_names.add(dedupe_key)

                pending_states.append(
                    State(
                        country_id=country_id,
                        name=str(state_name).strip(),
                    )
                )
                state_count += 1
                if len(pending_states) >= BATCH_SIZE:
                    _flush_batch(db, pending_states)

        _flush_batch(db, pending_states)
        print(f"Inserted {state_count} states.")

        states = db.scalars(select(State)).all()
        state_by_country_name: dict[tuple[int, str], int] = {
            (state.country_id, state.name.lower()): state.id for state in states
        }

        pending_cities: list[City] = []
        city_count = 0
        seen_city_keys: set[tuple[int, str]] = set()
        for row in hierarchy_data:
            country_id = country_by_name.get((row.get("name") or "").lower())
            if not country_id:
                continue

            for state_row in row.get("states") or []:
                if not isinstance(state_row, dict):
                    continue

                state_id = state_by_country_name.get(
                    (country_id, str(state_row.get("name") or "").strip().lower())
                )
                if not state_id:
                    continue

                for city_row in state_row.get("cities") or []:
                    city_name = city_row.get("name") if isinstance(city_row, dict) else city_row
                    if not city_name:
                        continue

                    dedupe_key = (state_id, str(city_name).strip().lower())
                    if dedupe_key in seen_city_keys:
                        continue
                    seen_city_keys.add(dedupe_key)

                    pending_cities.append(
                        City(
                            country_id=country_id,
                            state_id=state_id,
                            name=str(city_name).strip(),
                        )
                    )
                    city_count += 1
                    if len(pending_cities) >= BATCH_SIZE:
                        _flush_batch(db, pending_cities)

        _flush_batch(db, pending_cities)

        final_states = db.scalar(select(func.count()).select_from(State)) or 0
        final_cities = db.scalar(select(func.count()).select_from(City)) or 0
        states_without_cities = db.scalar(
            select(func.count())
            .select_from(State)
            .outerjoin(City, City.state_id == State.id)
            .where(City.id.is_(None))
        ) or 0

        print(f"Inserted {final_cities} cities under {final_states} states.")
        print(f"States without cities: {states_without_cities}")


if __name__ == "__main__":
    force_seed = "--force" in sys.argv
    seed_location_master(force=force_seed)
