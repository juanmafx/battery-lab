# Distribution-free trend statistics: Mann-Kendall with Hamed-Rao correction and the Theil-Sen estimator.
import itertools
import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

DEFAULT_MAX_PAIRS = 250_000


@dataclass(frozen=True)
class MannKendall:
    n: int
    s: int
    variance: float
    variance_inflation: float
    z: float
    p_value: float


def require_increasing(times: Sequence[float], values: Sequence[float]) -> None:
    if len(times) != len(values):
        raise ValueError("times and values must have the same length")
    if any(later <= earlier for earlier, later in itertools.pairwise(times)):
        raise ValueError("times must be strictly increasing")


def average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        rank = (start + stop + 1) / 2
        for position in range(start, stop):
            ranks[order[position]] = rank
        start = stop
    return ranks


def kendall_s(values: Sequence[float]) -> int:
    dense = {value: index + 1 for index, value in enumerate(sorted(set(values)))}
    tree = [0] * (len(dense) + 1)
    total = 0
    for seen, value in enumerate(values):
        rank = dense[value]
        lower, position = 0, rank - 1
        while position > 0:
            lower += tree[position]
            position -= position & -position
        at_most, position = 0, rank
        while position > 0:
            at_most += tree[position]
            position -= position & -position
        total += lower - (seen - at_most)
        position = rank
        while position < len(tree):
            tree[position] += 1
            position += position & -position
    return total


def tied_variance(values: Sequence[float]) -> float:
    n = len(values)
    ties = sum(size * (size - 1) * (2 * size + 5) for size in Counter(values).values())
    return (n * (n - 1) * (2 * n + 5) - ties) / 18


def variance_inflation(times: Sequence[float], values: Sequence[float], slope: float) -> float:
    n = len(values)
    if n < 4:
        return 1.0
    ranks = average_ranks([value - slope * moment for moment, value in zip(times, values, strict=True)])
    mean = sum(ranks) / n
    centered = [rank - mean for rank in ranks]
    energy = sum(value * value for value in centered)
    if energy == 0:
        return 1.0
    max_lag = min(n - 3, max(1, math.ceil(10 * math.log10(n))))
    weighted = 0.0
    for lag in range(1, max_lag + 1):
        rho = sum(centered[index] * centered[index + lag] for index in range(n - lag)) / energy
        spread = 1.96 * math.sqrt(n - lag - 1)
        if (-1 - spread) / (n - lag) <= rho <= (-1 + spread) / (n - lag):
            continue
        weighted += (n - lag) * (n - lag - 1) * (n - lag - 2) * rho
    return max(1.0, 1 + 2 * weighted / (n * (n - 1) * (n - 2)))


def mann_kendall(times: Sequence[float], values: Sequence[float], slope: float) -> MannKendall:
    require_increasing(times, values)
    s = kendall_s(values)
    inflation = variance_inflation(times, values, slope)
    variance = tied_variance(values) * inflation
    if variance <= 0 or s == 0:
        return MannKendall(len(values), s, max(variance, 0.0), inflation, 0.0, 1.0)
    z = (s - math.copysign(1, s)) / math.sqrt(variance)
    return MannKendall(len(values), s, variance, inflation, z, math.erfc(abs(z) / math.sqrt(2)))


def pair_count(n: int) -> int:
    return n * (n - 1) // 2


def pairwise_slopes(
    times: Sequence[float], values: Sequence[float], max_pairs: int = DEFAULT_MAX_PAIRS, seed: int = 0
) -> list[float]:
    require_increasing(times, values)
    n = len(values)
    if pair_count(n) <= max_pairs:
        slopes = [
            (values[later] - values[earlier]) / (times[later] - times[earlier])
            for earlier in range(n)
            for later in range(earlier + 1, n)
        ]
    else:
        generator = random.Random(seed)
        slopes = []
        for _ in range(max_pairs):
            first = generator.randrange(n)
            second = generator.randrange(n - 1)
            second += second >= first
            earlier, later = min(first, second), max(first, second)
            slopes.append((values[later] - values[earlier]) / (times[later] - times[earlier]))
    slopes.sort()
    return slopes


def order_statistic(ordered: Sequence[float], rank: float) -> float:
    bounded = min(max(rank, 1.0), float(len(ordered)))
    below = math.floor(bounded)
    fraction = bounded - below
    if fraction == 0:
        return ordered[below - 1]
    return ordered[below - 1] + fraction * (ordered[below] - ordered[below - 1])


def median_of_sorted(ordered: Sequence[float]) -> float:
    return order_statistic(ordered, (len(ordered) + 1) / 2)


def sen_interval(ordered: Sequence[float], total_pairs: int, variance: float, confidence: float) -> tuple[float, float]:
    half_width = NormalDist().inv_cdf((1 + confidence) / 2) * math.sqrt(max(variance, 0.0))
    scale = len(ordered) / total_pairs
    lower_rank = (total_pairs - half_width) / 2 * scale
    upper_rank = ((total_pairs + half_width) / 2 + 1) * scale
    return order_statistic(ordered, lower_rank), order_statistic(ordered, upper_rank)
