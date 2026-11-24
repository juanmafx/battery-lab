from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

FieldValue = int | str | None

CORE_FIELDS = (
    "status",
    "capacity",
    "capacity_level",
    "charge_now",
    "charge_full",
    "charge_full_design",
    "energy_now",
    "energy_full",
    "energy_full_design",
    "voltage_now",
    "voltage_min_design",
    "current_now",
    "power_now",
    "cycle_count",
    "technology",
    "model_name",
    "manufacturer",
    "serial_number",
)
TEXT_FIELDS = frozenset({"status", "capacity_level", "technology", "model_name", "manufacturer", "serial_number"})
NUMERIC_FIELDS = frozenset(CORE_FIELDS) - TEXT_FIELDS
RECORD_FIELDS = ("machine_id", "timestamp", "battery", *CORE_FIELDS, "health_pct", "temp_c", "extra")


@dataclass(frozen=True)
class MachineId:
    value: str
    source: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class BatterySample:
    machine_id: str
    timestamp: datetime
    battery: str
    status: str | None = None
    capacity: int | None = None
    capacity_level: str | None = None
    charge_now: int | None = None
    charge_full: int | None = None
    charge_full_design: int | None = None
    energy_now: int | None = None
    energy_full: int | None = None
    energy_full_design: int | None = None
    voltage_now: int | None = None
    voltage_min_design: int | None = None
    current_now: int | None = None
    power_now: int | None = None
    cycle_count: int | None = None
    technology: str | None = None
    model_name: str | None = None
    manufacturer: str | None = None
    serial_number: str | None = None
    temp_c: float | None = None
    extra: Mapping[str, FieldValue] = field(default_factory=dict, hash=False)

    @classmethod
    def from_reading(
        cls,
        machine_id: str,
        timestamp: datetime,
        battery: str,
        values: Mapping[str, FieldValue],
        temp_c: float | None = None,
    ) -> "BatterySample":
        core: dict[str, Any] = {name: values.get(name) for name in CORE_FIELDS}
        extra = {key: value for key, value in sorted(values.items()) if key not in core}
        return cls(machine_id=machine_id, timestamp=timestamp, battery=battery, temp_c=temp_c, extra=extra, **core)

    @property
    def health_pct(self) -> float | None:
        pairs = ((self.charge_full, self.charge_full_design), (self.energy_full, self.energy_full_design))
        for full, design in pairs:
            if full is not None and design is not None and full > 0 and design > 0:
                return round(full / design * 100, 2)
        return None

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {name: getattr(self, name) for name in RECORD_FIELDS}
        record["timestamp"] = self.timestamp.isoformat(timespec="seconds")
        record["extra"] = dict(self.extra)
        return record


@dataclass(frozen=True)
class Gap:
    start: datetime
    end: datetime

    @property
    def seconds(self) -> float:
        return (self.end - self.start).total_seconds()


@dataclass(frozen=True)
class HealthDelta:
    first: BatterySample
    last: BatterySample
    first_pct: float
    last_pct: float

    @property
    def delta_pp(self) -> float:
        return round(self.last_pct - self.first_pct, 2)


@dataclass(frozen=True)
class StatusTimeline:
    durations: Mapping[str, float] = field(default_factory=dict, hash=False)
    changes: Mapping[tuple[str, str], int] = field(default_factory=dict, hash=False)
    gaps: tuple[Gap, ...] = ()

    @property
    def tracked_seconds(self) -> float:
        return sum(self.durations.values())

    @property
    def gap_seconds(self) -> float:
        return sum(gap.seconds for gap in self.gaps)

    @property
    def change_count(self) -> int:
        return sum(self.changes.values())


@dataclass(frozen=True)
class TemperatureStats:
    minimum: float
    median: float
    maximum: float
    count: int


@dataclass(frozen=True)
class BatterySummary:
    machine_id: str
    battery: str
    samples: tuple[BatterySample, ...]
    health: HealthDelta | None
    timeline: StatusTimeline
    temperature: TemperatureStats | None

    @property
    def first(self) -> BatterySample:
        return self.samples[0]

    @property
    def last(self) -> BatterySample:
        return self.samples[-1]

    @property
    def span_seconds(self) -> float:
        return (self.last.timestamp - self.first.timestamp).total_seconds()

    @property
    def cycle_count(self) -> int | None:
        counts = [sample.cycle_count for sample in self.samples if sample.cycle_count is not None]
        return counts[-1] if counts else None
