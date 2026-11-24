import re
from pathlib import Path

from battery_lab.models import MachineId
from battery_lab.readers import read_text

IDENTITY_FIELDS = ("product_name", "product_sku")


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (read_text(path) or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip().removeprefix("export ").strip()] = value.strip().strip("'\"")
    return values


def machine_id(env_file: Path | None = None, sysfs_root: Path = Path("/sys")) -> MachineId:
    if env_file is not None:
        configured = read_env(env_file).get("MACHINE_ID")
        if configured:
            return MachineId(configured, "env")
    dmi = sysfs_root / "class" / "dmi" / "id"
    parts = [read_text(dmi / name) for name in IDENTITY_FIELDS]
    joined = "-".join(part for part in parts if part)
    if joined:
        return MachineId(re.sub(r"\s+", "-", joined), "dmi")
    return MachineId("unknown", "unknown")
