from pathlib import Path

from battery_lab.readers import parse_int, read_text

MAX_PLAUSIBLE_MILLI_C = 150_000


def read_zones(sysfs_root: Path = Path("/sys")) -> dict[str, int | None]:
    try:
        zones = sorted((sysfs_root / "class" / "thermal").glob("thermal_zone*"))
    except OSError:
        return {}
    return {zone.name: parse_int(read_text(zone / "temp")) for zone in zones}


def max_temp_c(sysfs_root: Path = Path("/sys")) -> float | None:
    readings = [value for value in read_zones(sysfs_root).values() if value is not None]
    plausible = [value for value in readings if 0 < value <= MAX_PLAUSIBLE_MILLI_C]
    return max(plausible) / 1000 if plausible else None
