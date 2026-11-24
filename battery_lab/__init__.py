from datetime import datetime
from pathlib import Path

from battery_lab.analysis.summary import health_delta, status_timeline, summarize, temperature_stats
from battery_lab.analysis.trend import HealthTrend, health_trend
from battery_lab.models import BatterySample, BatterySummary, HealthDelta, MachineId, StatusTimeline
from battery_lab.readers.dmi import machine_id
from battery_lab.readers.power_supply import read_batteries
from battery_lab.readers.thermal import max_temp_c
from battery_lab.storage import SampleStore, StorageError
from battery_lab.storage.csv_store import CsvStore

__version__ = "1.0.1"

__all__ = [
    "BatterySample",
    "BatterySummary",
    "CsvStore",
    "HealthDelta",
    "HealthTrend",
    "MachineId",
    "SampleStore",
    "StatusTimeline",
    "StorageError",
    "__version__",
    "collect_samples",
    "health_delta",
    "health_trend",
    "status_timeline",
    "summarize",
    "temperature_stats",
]


def collect_samples(
    sysfs_root: Path = Path("/sys"),
    env_file: Path | None = None,
    now: datetime | None = None,
) -> list[BatterySample]:
    identity = machine_id(env_file, sysfs_root)
    moment = now or datetime.now()
    timestamp = (moment if moment.tzinfo else moment.astimezone()).replace(microsecond=0)
    temp_c = max_temp_c(sysfs_root)
    return [
        BatterySample.from_reading(identity.value, timestamp, name, values, temp_c)
        for name, values in read_batteries(sysfs_root)
    ]
