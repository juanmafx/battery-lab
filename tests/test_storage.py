import csv
from dataclasses import fields

import pytest

from battery_lab import collect_samples
from battery_lab.models import CORE_FIELDS, BatterySample
from battery_lab.storage import SampleStore, StorageError
from battery_lab.storage.csv_store import HEADER, CsvStore

LEGACY_HEADER = [name for name in HEADER if name != "temp_c"]


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def write_dict_rows(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, restval="")
        writer.writeheader()
        writer.writerows(rows)


def test_sample_fields_follow_the_record_schema():
    assert [field.name for field in fields(BatterySample)] == ["machine_id", "timestamp", "battery", *CORE_FIELDS, "temp_c", "extra"]
    assert HEADER[-3:] == ["health_pct", "temp_c", "extra"]


def test_csv_store_satisfies_the_sample_store_interface(tmp_path):
    assert isinstance(CsvStore(tmp_path / "battery.csv"), SampleStore)


def test_append_writes_header_once_and_round_trips(tmp_path, make_sample):
    store = CsvStore(tmp_path / "data" / "battery.csv")
    first = [make_sample(0, temp_c=63.05, extra={"present": 1, "type": "Battery"})]
    second = [make_sample(5, status="Discharging", current_now=-1500)]
    store.append(first)
    store.append(second)
    rows = read_rows(store.path)
    assert rows[0] == HEADER
    assert len(rows) == 3
    assert store.load() == first + second


def test_nulls_are_written_as_empty_cells(tmp_path, make_sample):
    store = CsvStore(tmp_path / "battery.csv")
    store.append([make_sample(cycle_count=None, temp_c=None)])
    with store.path.open(newline="", encoding="utf-8") as handle:
        [row] = list(csv.DictReader(handle))
    assert row["cycle_count"] == ""
    assert row["temp_c"] == ""
    assert row["extra"] == ""
    assert row["health_pct"] == "83.64"


def test_empty_file_is_treated_as_new(tmp_path, make_sample):
    path = tmp_path / "battery.csv"
    path.write_text("")
    CsvStore(path).append([make_sample()])
    assert read_rows(path)[0] == HEADER


def test_legacy_header_is_migrated_in_place(tmp_path, make_sample):
    path = tmp_path / "battery.csv"
    legacy = {
        "machine_id": "OLD",
        "timestamp": "2026-09-13T23:38:03-03:00",
        "battery": "BAT0",
        "status": "Not charging",
        "charge_full": "2956000",
        "charge_full_design": "3534000",
        "health_pct": "83.64",
    }
    write_dict_rows(path, LEGACY_HEADER, [legacy])
    store = CsvStore(path)
    store.append([make_sample(machine_id="NEW", temp_c=93.0)])
    assert read_rows(path)[0] == HEADER
    old, new = store.load()
    assert (old.machine_id, old.status, old.health_pct, old.temp_c) == ("OLD", "Not charging", 83.64, None)
    assert (new.machine_id, new.temp_c) == ("NEW", 93.0)
    assert not path.with_name("battery.csv.tmp").exists()


@pytest.mark.parametrize(
    "content",
    [
        "machine_id,timestamp,mystery\nx,2026-09-13T00:00:00-03:00,1\n",
        "machine_id,timestamp\nx,2026-09-13T00:00:00-03:00,extra-cell\n",
        "machine_id,machine_id\n",
    ],
    ids=["unknown-column", "ragged-row", "duplicate-column"],
)
def test_unrecognized_csv_is_refused_and_left_untouched(tmp_path, make_sample, content):
    path = tmp_path / "battery.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(StorageError):
        CsvStore(path).append([make_sample()])
    assert path.read_text(encoding="utf-8") == content


def test_load_missing_file_is_empty(tmp_path):
    assert CsvStore(tmp_path / "absent.csv").load() == []


def test_load_skips_bad_timestamps_and_nulls_bad_cells(tmp_path):
    path = tmp_path / "battery.csv"
    write_dict_rows(
        path,
        HEADER,
        [
            {"machine_id": "M", "timestamp": "not-a-date", "battery": "BAT0"},
            {"machine_id": "M", "timestamp": "2026-09-13T23:38:03", "battery": "BAT0", "capacity": "abc", "temp_c": "nan", "extra": "{broken"},
        ],
    )
    [sample] = CsvStore(path).load()
    assert sample.timestamp.tzinfo is not None
    assert sample.capacity is None
    assert sample.temp_c is None
    assert sample.extra == {}


@pytest.mark.parametrize(
    "machine", ["dell_latitude_3410", "hp_elitebook_840_energy", "lenovo_thinkpad_t480_dual", "asus_zenbook_malformed"]
)
def test_fixture_machines_round_trip_through_csv(tmp_path, fake_sys, machine):
    samples = collect_samples(fake_sys(machine))
    store = CsvStore(tmp_path / "battery.csv")
    store.append(samples)
    assert store.load() == samples
