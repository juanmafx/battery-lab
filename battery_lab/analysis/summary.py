import itertools
import statistics
from collections.abc import Iterable, Sequence

from battery_lab.models import BatterySample, BatterySummary, Gap, HealthDelta, StatusTimeline, TemperatureStats

DEFAULT_GAP_FACTOR = 3.0
UNKNOWN_STATUS = "(unknown)"


def in_time_order(samples: Iterable[BatterySample]) -> list[BatterySample]:
    return sorted(samples, key=lambda sample: sample.timestamp)


def health_delta(samples: Iterable[BatterySample]) -> HealthDelta | None:
    measured = [(sample, pct) for sample in in_time_order(samples) if (pct := sample.health_pct) is not None]
    if not measured:
        return None
    (first, first_pct), (last, last_pct) = measured[0], measured[-1]
    return HealthDelta(first=first, last=last, first_pct=first_pct, last_pct=last_pct)


def gap_limit(intervals: Sequence[float], factor: float = DEFAULT_GAP_FACTOR) -> float | None:
    positive = [seconds for seconds in intervals if seconds > 0]
    return statistics.median(positive) * factor if positive else None


def status_timeline(samples: Iterable[BatterySample], gap_factor: float = DEFAULT_GAP_FACTOR) -> StatusTimeline:
    ordered = in_time_order(samples)
    pairs = list(itertools.pairwise(ordered))
    intervals = [(later.timestamp - earlier.timestamp).total_seconds() for earlier, later in pairs]
    limit = gap_limit(intervals, gap_factor)
    if limit is None:
        return StatusTimeline()
    durations: dict[str, float] = {}
    changes: dict[tuple[str, str], int] = {}
    gaps: list[Gap] = []
    for (earlier, later), seconds in zip(pairs, intervals, strict=False):
        if seconds <= 0:
            continue
        if seconds > limit:
            gaps.append(Gap(start=earlier.timestamp, end=later.timestamp))
            continue
        status = earlier.status or UNKNOWN_STATUS
        next_status = later.status or UNKNOWN_STATUS
        durations[status] = durations.get(status, 0.0) + seconds
        if status != next_status:
            changes[(status, next_status)] = changes.get((status, next_status), 0) + 1
    return StatusTimeline(durations=durations, changes=changes, gaps=tuple(gaps))


def temperature_stats(samples: Iterable[BatterySample]) -> TemperatureStats | None:
    temps = [sample.temp_c for sample in samples if sample.temp_c is not None]
    if not temps:
        return None
    return TemperatureStats(minimum=min(temps), median=statistics.median(temps), maximum=max(temps), count=len(temps))


def summarize(samples: Iterable[BatterySample], gap_factor: float = DEFAULT_GAP_FACTOR) -> list[BatterySummary]:
    groups: dict[tuple[str, str], list[BatterySample]] = {}
    for sample in samples:
        groups.setdefault((sample.machine_id, sample.battery), []).append(sample)
    summaries = []
    for (machine, battery), group in groups.items():
        ordered = tuple(in_time_order(group))
        summaries.append(
            BatterySummary(
                machine_id=machine,
                battery=battery,
                samples=ordered,
                health=health_delta(ordered),
                timeline=status_timeline(ordered, gap_factor),
                temperature=temperature_stats(ordered),
            )
        )
    return summaries
