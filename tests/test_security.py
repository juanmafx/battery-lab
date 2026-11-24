import csv
import multiprocessing
import stat
from datetime import UTC, datetime

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from battery_lab.cli import main
from battery_lab.cli.render import render_sample, safe_text
from battery_lab.models import BatterySample
from battery_lab.readers import MAX_ATTRIBUTE_CHARS, read_text
from battery_lab.readers.power_supply import normalize
from battery_lab.storage import StorageError
from battery_lab.storage.csv_store import HEADER, CsvStore, escape_cell, parse_extra, parse_timestamp, unescape_cell

MOMENT = datetime(2026, 1, 1, tzinfo=UTC)
LEGACY_HEADER = [name for name in HEADER if name != "temp_c"]


def write_rows(path, count):
    store = CsvStore(path)
    for index in range(count):
        store.append([BatterySample("M", MOMENT.replace(minute=index % 60), "BAT0", capacity=index % 100)])


@pytest.mark.parametrize("payload", ["=1+1", "+1", "-1", "@SUM(A1)", "\tx", "\rx"])
def test_formula_cells_are_neutralized_on_disk_and_restored(tmp_path, payload):
    store = CsvStore(tmp_path / "battery.csv")
    sample = BatterySample(payload, MOMENT, "BAT0", model_name=payload, manufacturer=payload)
    store.append([sample])
    with store.path.open(newline="", encoding="utf-8") as handle:
        [row] = list(csv.DictReader(handle))
    assert row["machine_id"].startswith("'")
    assert row["model_name"].startswith("'")
    assert store.load() == [sample]


def test_negative_numeric_cells_are_not_escaped(tmp_path):
    store = CsvStore(tmp_path / "battery.csv")
    store.append([BatterySample("M", MOMENT, "BAT0", current_now=-1500)])
    with store.path.open(newline="", encoding="utf-8") as handle:
        [row] = list(csv.DictReader(handle))
    assert row["current_now"] == "-1500"


@given(st.text(max_size=30))
def test_cell_escaping_round_trips(value):
    assert unescape_cell(escape_cell(value)) == value


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=60)
@given(st.text(alphabet=st.characters(exclude_categories=["Cs"]), min_size=1, max_size=20))
def test_text_fields_round_trip_through_csv(tmp_path, value):
    path = tmp_path / "round_trip.csv"
    path.unlink(missing_ok=True)
    sample = BatterySample("M", MOMENT, "BAT0", model_name=value)
    CsvStore(path).append([sample])
    assert CsvStore(path).load()[0].model_name == value


def test_new_log_is_private_to_the_user(tmp_path):
    store = CsvStore(tmp_path / "nested" / "battery.csv")
    store.append([BatterySample("M", MOMENT, "BAT0")])
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.path.parent.stat().st_mode) == 0o700


def test_migration_keeps_existing_permissions_and_leaves_no_staging_file(tmp_path):
    path = tmp_path / "battery.csv"
    path.write_text(",".join(LEGACY_HEADER) + "\r\n")
    path.chmod(0o640)
    CsvStore(path).append([BatterySample("M", MOMENT, "BAT0")])
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert [entry.name for entry in tmp_path.iterdir()] == ["battery.csv"]


def test_migration_does_not_follow_a_planted_staging_symlink(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me")
    path = tmp_path / "battery.csv"
    path.write_text(",".join(LEGACY_HEADER) + "\r\n")
    (tmp_path / "battery.csv.tmp").symlink_to(victim)
    CsvStore(path).append([BatterySample("M", MOMENT, "BAT0")])
    assert victim.read_text() == "keep me"


def test_truncated_final_row_does_not_corrupt_the_next_append(tmp_path):
    store = CsvStore(tmp_path / "battery.csv")
    store.append([BatterySample("FIRST", MOMENT, "BAT0")])
    with store.path.open("a", encoding="utf-8", newline="") as handle:
        handle.write("PARTIAL,not-a-time")
    store.append([BatterySample("LAST", MOMENT, "BAT0")])
    assert [sample.machine_id for sample in store.load()] == ["FIRST", "LAST"]


def test_concurrent_appends_keep_one_header_and_every_row(tmp_path):
    path = tmp_path / "battery.csv"
    context = multiprocessing.get_context("fork")
    workers = [context.Process(target=write_rows, args=(path, 25)) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(30)
    assert all(worker.exitcode == 0 for worker in workers)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert sum(row == HEADER for row in rows) == 1
    assert len(rows) == 101
    assert all(len(row) == len(HEADER) for row in rows)


@pytest.mark.parametrize(
    "payload",
    ["\x1b[2J", "\x1b]0;title\x07", "a\x08b", "right‮left", "zero​width", "line\nbreak"],
)
def test_control_and_format_characters_are_removed_from_terminal_output(payload):
    cleaned = safe_text(payload)
    assert "?" in cleaned
    assert not any(ord(char) < 32 or char in "\x7f‮​" for char in cleaned)


def test_show_and_collect_output_cannot_carry_escape_sequences(tmp_path, capsys):
    data = tmp_path / "battery.csv"
    hostile = BatterySample("\x1b[31mM", MOMENT, "\x1b[2J", status="\x1b]0;x\x07", model_name="\x1b[5m")
    CsvStore(data).append([hostile])
    assert main(["show", "--data", str(data)]) == 0
    assert "\x1b" not in capsys.readouterr().out
    assert "\x1b" not in render_sample(hostile, "dest")


def test_oversized_integer_in_uevent_does_not_crash():
    huge = "9" * 5000
    assert normalize("vendor_counter", huge) == huge
    assert normalize("capacity", huge) is None


def test_attribute_reads_are_bounded(tmp_path):
    path = tmp_path / "attribute"
    path.write_text("x" * (MAX_ATTRIBUTE_CHARS + 100))
    assert len(read_text(path)) == MAX_ATTRIBUTE_CHARS


def test_deeply_nested_extra_is_ignored():
    assert parse_extra("[" * 200_000) == {}


@pytest.mark.parametrize("value", ["0001-01-01T00:00:00", "9999-12-31T23:59:59", "garbage", "", None])
def test_extreme_timestamps_never_raise(value):
    parsed = parse_timestamp(value)
    assert parsed is None or parsed.tzinfo is not None


@pytest.mark.parametrize(
    "content",
    [b"\xff\xfe\x00broken", b"machine_id,timestamp\n" + b"x" * 200_000 + b",y\n"],
    ids=["invalid-utf8", "oversized-field"],
)
def test_unreadable_log_is_a_clean_error(tmp_path, capsys, content):
    data = tmp_path / "battery.csv"
    data.write_bytes(content)
    with pytest.raises(StorageError):
        CsvStore(data).load()
    assert main(["show", "--data", str(data)]) == 1
    assert capsys.readouterr().err.startswith("error:")
    assert data.read_bytes() == content


def test_append_to_a_directory_is_a_clean_error(tmp_path):
    target = tmp_path / "battery.csv"
    target.mkdir()
    with pytest.raises(StorageError):
        CsvStore(target).append([BatterySample("M", MOMENT, "BAT0")])


def test_serial_from_dmi_is_absent_from_records(fake_sys, capsys, tmp_path):
    assert main(["json", "--sysfs-root", str(fake_sys("dell_latitude_3410")), "--env-file", str(tmp_path / ".env")]) == 0
    assert "ROOT-ONLY" not in capsys.readouterr().out
