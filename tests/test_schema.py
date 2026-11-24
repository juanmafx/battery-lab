import json
import sqlite3
import tomllib
from pathlib import Path

import pytest

import battery_lab
from battery_lab.models import RECORD_FIELDS

REPO = Path(__file__).resolve().parents[1]
SCHEMA = (REPO / "db" / "schema.sql").read_text(encoding="utf-8")


@pytest.fixture
def database():
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA)
    connection.execute("INSERT INTO machines (id, machine_key) VALUES (1, 'M')")
    connection.execute("INSERT INTO batteries (id, machine_id, name) VALUES (1, 1, 'BAT0')")
    yield connection
    connection.close()


def insert(connection, **values):
    row = {"battery_id": 1, "recorded_at": "2026-01-01T00:00:00+00:00", **values}
    columns = ", ".join(row)
    placeholders = ", ".join("?" for _ in row)
    connection.execute(f"INSERT INTO samples ({columns}) VALUES ({placeholders})", tuple(row.values()))


def test_schema_is_idempotent(database):
    database.executescript(SCHEMA)


def test_view_columns_match_the_record_contract(database):
    cursor = database.execute("SELECT * FROM sample_records")
    assert tuple(column[0] for column in cursor.description) == RECORD_FIELDS


@pytest.mark.parametrize(
    ("columns", "expected"),
    [
        ({"charge_full": 2956000, "charge_full_design": 3534000}, 83.64),
        ({"energy_full": 47700000, "energy_full_design": 53000000}, 90.0),
        ({"charge_full": 0, "charge_full_design": 3534000}, None),
    ],
)
def test_view_computes_health_like_the_model(database, columns, expected):
    insert(database, **columns)
    assert database.execute("SELECT health_pct FROM sample_records").fetchone()[0] == expected


@pytest.mark.parametrize(
    "columns",
    [
        {"capacity": 101},
        {"cycle_count": 0},
        {"temp_c": 151.0},
        {"charge_full": -1},
        {"extra": "not json"},
        {"extra": json.dumps([1])},
        {"recorded_at": "not-a-date"},
        {"battery_id": 99},
        {"capacity": "abc"},
    ],
)
def test_constraints_reject_invalid_rows(database, columns):
    database.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        insert(database, **columns)


def test_duplicate_sample_is_rejected(database):
    insert(database)
    with pytest.raises(sqlite3.IntegrityError):
        insert(database)


def test_parameterized_insert_stores_hostile_text_literally(database):
    payload = "'; DROP TABLE samples; --"
    insert(database, model_name=payload)
    assert database.execute("SELECT model_name FROM sample_records").fetchone()[0] == payload


def test_package_and_project_versions_agree():
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == battery_lab.__version__
