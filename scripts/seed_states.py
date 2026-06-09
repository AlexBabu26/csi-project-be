"""Deprecated: use scripts/seed_location_master.py for hierarchical country-state-city seeding."""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.auth.models  # noqa: F401
import app.units.models  # noqa: F401

from sqlalchemy import delete, func, select

from app.auth.models import Country, State
from app.common.db import session_scope

COUNTRIES_STATES_URL = (
    "https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/"
    "master/json/countries+states.json"
)
BATCH_SIZE = 1000


def _download_json(url: str) -> list[dict]:
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url, timeout=180) as response:
        return json.load(response)


def seed_states(*, force: bool = False) -> None:
    with session_scope() as db:
        existing_states = db.scalar(select(func.count()).select_from(State)) or 0
        if existing_states and not force:
            print(f"Skipping seed: {existing_states} states already present.")
            return

        countries = db.scalars(select(Country)).all()
        country_by_name = {country.name.lower(): country.id for country in countries}
        if not country_by_name:
            raise RuntimeError("Seed countries before seeding states.")

        if force and existing_states:
            print("Force mode enabled: clearing existing state data.")
            db.execute(delete(State))
            db.flush()

        countries_states_data = _download_json(COUNTRIES_STATES_URL)
        pending_states: list[State] = []
        inserted = 0

        for row in countries_states_data:
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
                inserted += 1

                if len(pending_states) >= BATCH_SIZE:
                    db.add_all(pending_states)
                    db.flush()
                    pending_states.clear()

        if pending_states:
            db.add_all(pending_states)
            db.flush()

        state_count = db.scalar(select(func.count()).select_from(State)) or 0
        print(f"Inserted {state_count} states.")


if __name__ == "__main__":
    force_seed = "--force" in sys.argv
    seed_states(force=force_seed)
