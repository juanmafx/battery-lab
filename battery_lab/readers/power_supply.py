import re
from pathlib import Path

from battery_lab.models import NUMERIC_FIELDS, TEXT_FIELDS, FieldValue
from battery_lab.readers import parse_int, read_text

BatteryReading = tuple[str, dict[str, FieldValue]]

NULL_UNLESS_POSITIVE = frozenset({"cycle_count"})
CANONICAL_INT = re.compile(r"-?(0|[1-9][0-9]*)")


def battery_dirs(sysfs_root: Path = Path("/sys")) -> list[Path]:
    try:
        return sorted(path for path in (sysfs_root / "class" / "power_supply").glob("BAT*") if path.is_dir())
    except OSError:
        return []


def parse_uevent(text: str | None) -> dict[str, str | None]:
    fields: dict[str, str | None] = {}
    for line in (text or "").split("\n"):
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            continue
        fields[key.removeprefix("POWER_SUPPLY_").lower()] = value.strip() or None
    return fields


def normalize(key: str, value: str | None) -> FieldValue:
    if value is None or key in TEXT_FIELDS:
        return value
    if key in NUMERIC_FIELDS:
        number = parse_int(value)
        if number is None or (key in NULL_UNLESS_POSITIVE and number <= 0):
            return None
        return number
    if not CANONICAL_INT.fullmatch(value):
        return value
    number = parse_int(value)
    return value if number is None else number


def read_battery(path: Path) -> BatteryReading:
    fields = parse_uevent(read_text(path / "uevent"))
    name = fields.pop("name", None) or path.name
    return name, {key: normalize(key, value) for key, value in fields.items()}


def read_batteries(sysfs_root: Path = Path("/sys")) -> list[BatteryReading]:
    return [read_battery(path) for path in battery_dirs(sysfs_root)]
