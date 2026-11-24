#!/usr/bin/env python3
# Seeded Monte Carlo check of the trend estimators. Prints measured rates; run from the repository root.
import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from battery_lab.analysis.robust import (
    kendall_s,
    mann_kendall,
    median_of_sorted,
    pair_count,
    pairwise_slopes,
    sen_interval,
    tied_variance,
)


def fit(values: list[float]) -> tuple[float, float, float]:
    times = [float(index) for index in range(len(values))]
    ordered = pairwise_slopes(times, values)
    slope = median_of_sorted(ordered)
    test = mann_kendall(times, values, slope)
    lower, upper = sen_interval(ordered, pair_count(len(values)), test.variance, 0.95)
    return test.p_value, lower, upper


def naive_p_value(values: list[float]) -> float:
    s = kendall_s(values)
    if s == 0:
        return 1.0
    return math.erfc(((abs(s) - 1) / math.sqrt(tied_variance(values))) / math.sqrt(2))


def ar1(generator: random.Random, size: int, rho: float) -> list[float]:
    value = generator.gauss(0, 1)
    series = []
    for _ in range(size):
        value = rho * value + generator.gauss(0, math.sqrt(1 - rho * rho))
        series.append(value)
    return series


def main() -> int:
    parser = argparse.ArgumentParser(description="Seeded Monte Carlo check of the trend estimators.")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--runs", type=int, default=2000)
    parser.add_argument("--size", type=int, default=60)
    args = parser.parse_args()
    generator = random.Random(args.seed)

    white = sum(fit([generator.gauss(0, 1) for _ in range(args.size)])[0] < 0.05 for _ in range(args.runs))
    true_slope = -0.02
    covered = 0
    for _ in range(args.runs):
        _, lower, upper = fit([true_slope * index + generator.gauss(0, 1) for index in range(args.size)])
        covered += lower <= true_slope <= upper
    print(f"seed={args.seed} runs={args.runs} series_length={args.size} nominal_alpha=0.05")
    print(f"white noise false positive rate: {white / args.runs:.3f}")
    print(f"95% interval coverage, linear signal with white noise: {covered / args.runs:.3f}")
    for rho in (0.3, 0.6, 0.9):
        naive = corrected = 0
        for _ in range(args.runs):
            values = ar1(generator, args.size, rho)
            naive += naive_p_value(values) < 0.05
            corrected += fit(values)[0] < 0.05
        print(f"AR(1) rho={rho}: false positive rate uncorrected {naive / args.runs:.3f}, Hamed-Rao corrected {corrected / args.runs:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
