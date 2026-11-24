# Long-term health trend from daily medians, with a linear projection to a replacement threshold.
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, timedelta
from statistics import median

from battery_lab.analysis.robust import (
    DEFAULT_MAX_PAIRS,
    MannKendall,
    mann_kendall,
    median_of_sorted,
    pair_count,
    pairwise_slopes,
    sen_interval,
)
from battery_lab.models import BatterySample

DAYS_PER_YEAR = 365.2425
DEFAULT_SEED = 2026
DEFAULT_THRESHOLD_PCT = 70.0
MAX_PROJECTION_DAYS = 100 * 365
MIN_TREND_DAYS = 10


@dataclass(frozen=True)
class ThresholdCrossing:
    estimate: date
    earliest: date
    latest: date


@dataclass(frozen=True)
class HealthTrend:
    days_observed: int
    first_day: date
    last_day: date
    slope_pp_per_year: float
    slope_lower_pp_per_year: float
    slope_upper_pp_per_year: float
    fitted_last_pct: float
    mann_kendall: MannKendall
    confidence: float
    exact: bool
    seed: int
    threshold_pct: float
    verdict: str
    crossing: ThresholdCrossing | None


def daily_health(samples: Iterable[BatterySample]) -> list[tuple[date, float]]:
    days: dict[date, list[float]] = {}
    for sample in samples:
        health = sample.health_pct
        if health is not None:
            days.setdefault(sample.timestamp.astimezone(UTC).date(), []).append(health)
    return [(day, median(days[day])) for day in sorted(days)]


def project_crossing(
    last_day: date, fitted_last: float, threshold: float, slope: float, lower: float, upper: float
) -> ThresholdCrossing | None:
    if not (slope < 0 and upper < 0) or fitted_last <= threshold:
        return None
    drop = threshold - fitted_last
    offsets = [drop / (rate / DAYS_PER_YEAR) for rate in (slope, lower, upper)]
    if max(offsets) > MAX_PROJECTION_DAYS:
        return None
    estimate, earliest, latest = (last_day + timedelta(days=round(offset)) for offset in offsets)
    return ThresholdCrossing(estimate=estimate, earliest=earliest, latest=latest)


def classify(test: MannKendall, slope: float, confidence: float) -> str:
    if test.p_value >= 1 - confidence:
        return "no statistically significant trend"
    return "declining" if slope < 0 else "rising"


def health_trend(
    samples: Iterable[BatterySample],
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    confidence: float = 0.95,
    seed: int = DEFAULT_SEED,
    max_pairs: int = DEFAULT_MAX_PAIRS,
) -> HealthTrend | None:
    daily = daily_health(samples)
    if len(daily) < MIN_TREND_DAYS:
        return None
    origin = daily[0][0]
    times = [float((day - origin).days) for day, _ in daily]
    values = [value for _, value in daily]
    ordered = pairwise_slopes(times, values, max_pairs=max_pairs, seed=seed)
    slope = median_of_sorted(ordered)
    test = mann_kendall(times, values, slope)
    lower, upper = sen_interval(ordered, pair_count(len(values)), test.variance, confidence)
    intercept = median(values) - slope * median(times)
    fitted_last = intercept + slope * times[-1]
    yearly = (slope * DAYS_PER_YEAR, lower * DAYS_PER_YEAR, upper * DAYS_PER_YEAR)
    verdict = classify(test, slope, confidence)
    crossing = None
    if verdict == "declining":
        crossing = project_crossing(daily[-1][0], fitted_last, threshold_pct, *yearly)
    return HealthTrend(
        days_observed=len(daily),
        first_day=origin,
        last_day=daily[-1][0],
        slope_pp_per_year=yearly[0],
        slope_lower_pp_per_year=yearly[1],
        slope_upper_pp_per_year=yearly[2],
        fitted_last_pct=fitted_last,
        mann_kendall=test,
        confidence=confidence,
        exact=pair_count(len(values)) <= max_pairs,
        seed=seed,
        threshold_pct=threshold_pct,
        verdict=verdict,
        crossing=crossing,
    )
