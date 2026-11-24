import csv
import fcntl
import json
import math
import os
import stat
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from battery_lab.models import (
    CORE_FIELDS,
    NUMERIC_FIELDS,
    RECORD_FIELDS,
    TEXT_FIELDS,
    BatterySample,
    FieldValue,
    parse_bounded_int,
)
from battery_lab.storage import StorageError

HEADER = list(RECORD_FIELDS)
ESCAPED_FIELDS = TEXT_FIELDS | {"machine_id", "battery"}
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")
ESCAPE_MARK = "'"
READ_ERRORS = (OSError, csv.Error, UnicodeError)
READ_CHUNK_BYTES = 65_536


class CsvStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, samples: Iterable[BatterySample]) -> None:
        rows = [to_row(sample) for sample in samples]
        try:
            make_private_dirs(self.path.parent)
            with self.locked():
                existing = self.header()
                if existing is not None and existing != HEADER:
                    self.migrate(existing)
                descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC, 0o600)
                with os.fdopen(descriptor, "a", newline="", encoding="utf-8") as handle:
                    handle.write(self.repair_suffix())
                    writer = csv.DictWriter(handle, fieldnames=HEADER)
                    if existing is None:
                        writer.writeheader()
                    writer.writerows(rows)
        except READ_ERRORS as error:
            raise StorageError(f"cannot write {self.path}: {error}") from error

    def create(self, samples: Iterable[BatterySample]) -> None:
        rows = [to_row(sample) for sample in samples]
        try:
            make_private_dirs(self.path.parent)
            try:
                descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
            except FileExistsError as error:
                raise StorageError(f"{self.path} already exists; refusing to overwrite it") from error
            with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADER)
                writer.writeheader()
                writer.writerows(rows)
        except READ_ERRORS as error:
            raise StorageError(f"cannot write {self.path}: {error}") from error

    def load(self) -> list[BatterySample]:
        try:
            with self.path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except FileNotFoundError:
            return []
        except READ_ERRORS as error:
            raise StorageError(f"cannot read {self.path}: {error}") from error
        samples = (from_row(row) for row in rows)
        return [sample for sample in samples if sample is not None]

    def header(self) -> list[str] | None:
        try:
            with self.path.open(newline="", encoding="utf-8") as handle:
                return next(csv.reader(handle), None)
        except FileNotFoundError:
            return None

    def repair_suffix(self) -> str:
        with self.path.open("rb") as handle:
            if handle.seek(0, os.SEEK_END) == 0:
                return ""
            handle.seek(-1, os.SEEK_END)
            if handle.read(1) == b"\n":
                return ""
            handle.seek(0)
            quotes = sum(chunk.count(b'"') for chunk in iter(lambda: handle.read(READ_CHUNK_BYTES), b""))
        return '"\r\n' if quotes % 2 else "\r\n"

    @contextmanager
    def locked(self) -> Iterator[None]:
        descriptor = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def migrate(self, existing: list[str]) -> None:
        if len(set(existing)) != len(existing) or not set(existing) <= set(HEADER):
            raise StorageError(f"{self.path} has an unexpected header; refusing to append")
        with self.path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if any(None in row for row in rows):
            raise StorageError(f"{self.path} has rows longer than its header; refusing to migrate")
        target = self.path.resolve()
        mode = stat.S_IMODE(target.stat().st_mode)
        descriptor, staging = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADER, restval="")
                writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                os.fsync(handle.fileno())
                os.fchmod(handle.fileno(), mode)
            os.replace(staging, target)
        except BaseException:
            Path(staging).unlink(missing_ok=True)
            raise


def make_private_dirs(directory: Path) -> None:
    missing = []
    while not directory.exists():
        missing.append(directory)
        directory = directory.parent
    for path in reversed(missing):
        path.mkdir(mode=0o700, exist_ok=True)


def escape_cell(value: str) -> str:
    return ESCAPE_MARK + value if value.startswith((*FORMULA_PREFIXES, ESCAPE_MARK)) else value


def unescape_cell(value: str) -> str:
    if value.startswith(ESCAPE_MARK) and value[1:].startswith((*FORMULA_PREFIXES, ESCAPE_MARK)):
        return value[1:]
    return value


def to_row(sample: BatterySample) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for key, value in sample.to_record().items():
        if key == "extra":
            row[key] = json.dumps(value, sort_keys=True, separators=(",", ":")) if value else ""
        elif key in ESCAPED_FIELDS and isinstance(value, str):
            row[key] = escape_cell(value)
        else:
            row[key] = "" if value is None else value
    return row


def text_cell(value: str | None) -> str | None:
    return unescape_cell(value) if value else None


def from_row(row: dict[str, str | None]) -> BatterySample | None:
    timestamp = parse_timestamp(row.get("timestamp"))
    if timestamp is None:
        return None
    values: dict[str, Any] = {}
    for name in CORE_FIELDS:
        cell = row.get(name) or None
        values[name] = parse_bounded_int(cell) if name in NUMERIC_FIELDS else text_cell(cell)
    return BatterySample(
        machine_id=text_cell(row.get("machine_id")) or "unknown",
        timestamp=timestamp,
        battery=text_cell(row.get("battery")) or "unknown",
        temp_c=parse_float(row.get("temp_c")),
        extra=parse_extra(row.get("extra")),
        **values,
    )


def parse_timestamp(value: str | None) -> datetime | None:
    try:
        moment = datetime.fromisoformat(value or "")
        aware = moment if moment.tzinfo else moment.astimezone()
        aware.astimezone(UTC)
        return aware
    except (ValueError, OverflowError, OSError):
        return None


def parse_float(value: str | None) -> float | None:
    try:
        number = float(value) if value else None
    except ValueError:
        return None
    return number if number is not None and math.isfinite(number) else None


def parse_extra(value: str | None) -> dict[str, FieldValue]:
    try:
        decoded = json.loads(value) if value else {}
    except (ValueError, RecursionError):
        return {}
    return decoded if isinstance(decoded, dict) else {}
