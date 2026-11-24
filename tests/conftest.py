from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from battery_lab.models import BatterySample

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "fake_sys"
START = datetime(2026, 9, 13, 20, 0, tzinfo=timezone(timedelta(hours=-3)))


@pytest.fixture
def fake_sys():
    def resolve(machine):
        root = FIXTURES / machine
        assert root.is_dir(), f"no fixture named {machine}"
        return root

    return resolve


@pytest.fixture
def make_sample():
    def build(minutes=0, **overrides):
        values = {
            "machine_id": "TEST-MACHINE",
            "timestamp": START + timedelta(minutes=minutes),
            "battery": "BAT0",
            "status": "Not charging",
            "capacity": 75,
            "charge_full": 2956000,
            "charge_full_design": 3534000,
        }
        values.update(overrides)
        return BatterySample(**values)

    return build
