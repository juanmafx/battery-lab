import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

from battery_lab import collect_samples
from battery_lab.models import CORE_FIELDS, MachineId
from battery_lab.readers import dmi
from battery_lab.readers.power_supply import battery_dirs, parse_uevent, read_batteries
from battery_lab.readers.thermal import max_temp_c, read_zones

PACKAGE = Path(__file__).resolve().parents[1] / "battery_lab"
NOW = datetime(2026, 9, 13, 23, 38, 3, tzinfo=timezone(timedelta(hours=-3)))


def test_parse_uevent_strips_prefix_and_lowercases_keys():
    assert parse_uevent("POWER_SUPPLY_STATUS=Charging\nPOWER_SUPPLY_CAPACITY=80\n") == {
        "status": "Charging",
        "capacity": "80",
    }
    assert parse_uevent(None) == {}


def test_dell_reports_charge_fields_and_null_cycle_count(fake_sys):
    [sample] = collect_samples(fake_sys("dell_latitude_3410"), now=NOW)
    assert sample.battery == "BAT0"
    assert sample.machine_id == "Latitude-3410-09EC"
    assert sample.timestamp == NOW
    assert sample.status == "Not charging"
    assert (sample.charge_full, sample.charge_full_design) == (2956000, 3534000)
    assert sample.energy_full is None
    assert sample.cycle_count is None
    assert sample.health_pct == 83.64
    assert sample.serial_number == "0001"
    assert sample.temp_c == 82.0
    assert sample.extra == {"present": 1, "type": "Battery"}


def test_only_bat_entries_are_sampled(fake_sys):
    assert [path.name for path in battery_dirs(fake_sys("dell_latitude_3410"))] == ["BAT0"]


def test_energy_vendor_health_comes_from_energy_fields(fake_sys):
    [sample] = collect_samples(fake_sys("hp_elitebook_840_energy"), now=NOW)
    assert sample.charge_full is None
    assert (sample.energy_full, sample.energy_full_design) == (47700000, 53000000)
    assert sample.power_now == 7431000
    assert sample.cycle_count == 148
    assert sample.health_pct == 90.0


def test_two_batteries_produce_one_row_each_with_shared_context(fake_sys):
    samples = collect_samples(fake_sys("lenovo_thinkpad_t480_dual"), now=NOW)
    assert [sample.battery for sample in samples] == ["BAT0", "BAT1"]
    assert {sample.timestamp for sample in samples} == {NOW}
    assert {sample.machine_id for sample in samples} == {"20L5CTO1WW-LENOVO_MT_20L5_BU_Think_FM_ThinkPad-T480"}
    assert {sample.temp_c for sample in samples} == {64.0}
    assert [sample.health_pct for sample in samples] == [90.0, 80.0]
    assert [sample.cycle_count for sample in samples] == [402, 87]


def test_machine_without_battery_yields_no_samples(fake_sys):
    root = fake_sys("desktop_no_battery")
    assert read_batteries(root) == []
    assert collect_samples(root, now=NOW) == []
    assert max_temp_c(root) == 41.0


def test_malformed_uevent_never_raises_and_nulls_bad_values(fake_sys):
    bat0 = collect_samples(fake_sys("asus_zenbook_malformed"), now=NOW)[0]
    assert bat0.battery == "BAT0"
    assert bat0.status is None
    assert bat0.capacity is None
    assert bat0.cycle_count is None
    assert bat0.charge_full == 0
    assert bat0.health_pct is None
    assert bat0.voltage_now == 11
    assert bat0.model_name == "ASUS Battery"
    assert bat0.manufacturer == "ASUSTeK"
    assert bat0.technology is not None and bat0.technology.endswith("Li-ion")
    assert bat0.extra == {"vendor_blob": "a=b"}


def test_battery_directory_without_uevent_is_all_null(fake_sys):
    bat1 = collect_samples(fake_sys("asus_zenbook_malformed"), now=NOW)[1]
    assert bat1.battery == "BAT1"
    assert all(getattr(bat1, name) is None for name in CORE_FIELDS)
    assert bat1.extra == {}


def test_missing_sysfs_tree_yields_nothing(tmp_path):
    assert read_batteries(tmp_path) == []
    assert max_temp_c(tmp_path) is None
    assert dmi.machine_id(None, tmp_path) == MachineId("unknown", "unknown")


def test_thermal_uses_highest_readable_zone(fake_sys):
    root = fake_sys("dell_latitude_3410")
    zones = read_zones(root)
    assert zones["thermal_zone2"] == 82000
    assert zones["thermal_zone3"] is None
    assert max_temp_c(root) == 82.0


def test_thermal_ignores_implausible_readings(fake_sys):
    assert max_temp_c(fake_sys("asus_zenbook_malformed")) == 48.0


def test_thermal_keeps_millidegree_precision(tmp_path):
    zone = tmp_path / "class" / "thermal" / "thermal_zone0"
    zone.mkdir(parents=True)
    (zone / "temp").write_text("41050\n")
    assert max_temp_c(tmp_path) == 41.05


def test_env_machine_id_takes_precedence(fake_sys, tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\n\nexport MACHINE_ID='TEST-SERIAL-01'\n")
    assert dmi.machine_id(env, fake_sys("dell_latitude_3410")) == MachineId("TEST-SERIAL-01", "env")


def test_empty_or_missing_env_falls_back_to_dmi(fake_sys, tmp_path):
    root = fake_sys("dell_latitude_3410")
    empty = tmp_path / ".env"
    empty.write_text("MACHINE_ID=\n")
    expected = MachineId("Latitude-3410-09EC", "dmi")
    assert dmi.machine_id(empty, root) == expected
    assert dmi.machine_id(tmp_path / "absent.env", root) == expected


def test_dmi_without_sku_uses_product_name_alone(fake_sys):
    assert dmi.machine_id(None, fake_sys("asus_zenbook_malformed")).value == "ZenBook-UX425EA_UX425EA"


def test_product_serial_is_never_read(fake_sys, monkeypatch):
    opened = []
    real_read_text = dmi.read_text

    def spy(path):
        opened.append(Path(path).name)
        return real_read_text(path)

    monkeypatch.setattr(dmi, "read_text", spy)
    identity = dmi.machine_id(None, fake_sys("dell_latitude_3410"))
    assert opened == ["product_name", "product_sku"]
    assert "ROOT-ONLY" not in identity.value


def test_sysfs_paths_appear_only_as_default_arguments():
    offenders = []
    for source in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        allowed = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in [*node.args.defaults, *node.args.kw_defaults]:
                    if default is not None:
                        allowed.update(id(child) for child in ast.walk(default))
            elif isinstance(node, ast.keyword) and node.arg == "default":
                allowed.update(id(child) for child in ast.walk(node.value))
        for node in ast.walk(tree):
            is_sysfs_path = isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/sys")
            if is_sysfs_path and id(node) not in allowed:
                offenders.append(f"{source.relative_to(PACKAGE)}:{node.lineno}")
    assert offenders == []
