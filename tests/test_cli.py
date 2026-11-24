import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from battery_lab import __version__
from battery_lab.cli import default_home, format_duration, main
from battery_lab.storage.csv_store import CsvStore

REPO = Path(__file__).resolve().parents[1]


def sampling_args(root, tmp_path):
    return ["--sysfs-root", str(root), "--env-file", str(tmp_path / ".env")]


def load_shim():
    spec = importlib.util.spec_from_file_location("collect_shim", REPO / "collect.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collect_appends_one_row_per_battery(fake_sys, tmp_path, capsys):
    data = tmp_path / "battery.csv"
    assert main(["collect", *sampling_args(fake_sys("lenovo_thinkpad_t480_dual"), tmp_path), "--data", str(data)]) == 0
    assert [sample.battery for sample in CsvStore(data).load()] == ["BAT0", "BAT1"]
    assert "health 90.00%" in capsys.readouterr().out


def test_collect_without_battery_fails_and_writes_nothing(fake_sys, tmp_path, capsys):
    data = tmp_path / "battery.csv"
    assert main(["collect", *sampling_args(fake_sys("desktop_no_battery"), tmp_path), "--data", str(data)]) == 1
    assert not data.exists()
    assert "no battery found" in capsys.readouterr().err


def test_collect_reports_storage_errors(fake_sys, tmp_path, capsys):
    data = tmp_path / "battery.csv"
    data.write_text("unexpected,header\n")
    assert main(["collect", *sampling_args(fake_sys("dell_latitude_3410"), tmp_path), "--data", str(data)]) == 1
    assert capsys.readouterr().err.startswith("error:")


def test_json_prints_records_in_schema_order(fake_sys, tmp_path, capsys):
    assert main(["json", *sampling_args(fake_sys("dell_latitude_3410"), tmp_path)]) == 0
    [record] = json.loads(capsys.readouterr().out)
    assert record["cycle_count"] is None
    assert record["health_pct"] == 83.64
    assert record["temp_c"] == 82.0
    assert list(record)[-3:] == ["health_pct", "temp_c", "extra"]


def test_show_renders_health_status_and_temperature(tmp_path, make_sample, capsys):
    data = tmp_path / "battery.csv"
    CsvStore(data).append(
        [
            make_sample(0, temp_c=60.0),
            make_sample(5, status="Discharging", temp_c=70.0),
            make_sample(10),
        ]
    )
    assert main(["show", "--data", str(data)]) == 0
    out = capsys.readouterr().out
    assert "health         83.64% -> 83.64%  (delta +0.00 pp)" in out
    assert "cycle count    not reported by firmware" in out
    assert "temp_c         min 60.0 / median 65.0 / max 70.0 °C  (2 samples)" in out
    assert "Not charging -> Discharging: 1" in out


def test_show_without_samples_fails(tmp_path, capsys):
    assert main(["show", "--data", str(tmp_path / "absent.csv")]) == 1
    assert "no samples" in capsys.readouterr().out


def test_a_subcommand_is_required(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code == 2


@pytest.mark.parametrize(
    ("seconds", "text"),
    [(59, "59s"), (60, "1m"), (3 * 3600 + 120, "3h 02m"), (2 * 86400 + 3600, "2d 01h 00m")],
)
def test_format_duration(seconds, text):
    assert format_duration(seconds) == text


def test_default_home_is_the_checkout_when_running_from_source():
    assert default_home() == REPO


def test_shim_maps_legacy_flags_to_subcommands():
    shim = load_shim()
    assert shim.translate([]) == ["collect"]
    assert shim.translate(["--json"]) == ["json"]
    assert shim.translate(["--show", "--data", "x.csv"]) == ["show", "--data", "x.csv"]


def test_shim_runs_as_a_script_from_another_directory(fake_sys, tmp_path):
    command = [sys.executable, str(REPO / "collect.py"), "--json", *sampling_args(fake_sys("hp_elitebook_840_energy"), tmp_path)]
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)[0]["health_pct"] == 90.0


def test_python_dash_m_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "battery_lab", "--version"], cwd=REPO, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"battery-lab {__version__}"
