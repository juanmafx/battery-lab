from pathlib import Path

from battery_lab.models import parse_bounded_int

MAX_ATTRIBUTE_CHARS = 65_536


def read_text(path: Path) -> str | None:
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as handle:
            value = handle.read(MAX_ATTRIBUTE_CHARS).strip()
    except OSError:
        return None
    return value or None


def parse_int(value: str | None) -> int | None:
    return parse_bounded_int(value)
