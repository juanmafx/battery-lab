# Seeded synthetic logs for validating the estimators. Output is always labelled with a SYNTHETIC machine id.
import random
from datetime import UTC, datetime, timedelta

from battery_lab.analysis.trend import DAYS_PER_YEAR
from battery_lab.models import BatterySample

DESIGN_CAPACITY_UAH = 3_534_000
MAX_SIMULATION_DAYS = 36_525
SIMULATION_START = datetime(2026, 1, 1, tzinfo=UTC)
STATUS_CYCLE = ("Charging", "Not charging", "Discharging")


def simulate_samples(
    seed: int,
    days: int,
    start_health_pct: float = 90.0,
    fade_pp_per_year: float = 4.0,
    noise_pp: float = 0.15,
    samples_per_day: int = 4,
) -> list[BatterySample]:
    if days < 1 or samples_per_day < 1:
        raise ValueError("days and samples_per_day must be at least 1")
    if days > MAX_SIMULATION_DAYS:
        raise ValueError(f"days must be at most {MAX_SIMULATION_DAYS}")
    generator = random.Random(seed)
    step = timedelta(days=1) / samples_per_day
    samples = []
    for index in range(days * samples_per_day):
        elapsed_days = index / samples_per_day
        expected = start_health_pct - fade_pp_per_year * elapsed_days / DAYS_PER_YEAR
        health = max(1.0, min(100.0, expected + generator.gauss(0.0, noise_pp)))
        samples.append(
            BatterySample(
                machine_id=f"SYNTHETIC-{seed}",
                timestamp=SIMULATION_START + step * index,
                battery="BAT0",
                status=STATUS_CYCLE[index % len(STATUS_CYCLE)],
                capacity=60 + index % 16,
                charge_full=round(DESIGN_CAPACITY_UAH * health / 100),
                charge_full_design=DESIGN_CAPACITY_UAH,
            )
        )
    return samples
