import itertools
import math
import random
from statistics import median

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from battery_lab.analysis.robust import (
    average_ranks,
    kendall_s,
    mann_kendall,
    median_of_sorted,
    order_statistic,
    pair_count,
    pairwise_slopes,
    sen_interval,
    tied_variance,
    variance_inflation,
)

series = st.lists(st.integers(min_value=-40, max_value=40), min_size=2, max_size=40)
SIMULATIONS = 400


def brute_force_s(values):
    return sum((b > a) - (b < a) for a, b in itertools.combinations(values, 2))


def fit(values):
    times = [float(index) for index in range(len(values))]
    ordered = pairwise_slopes(times, values)
    slope = median_of_sorted(ordered)
    test = mann_kendall(times, values, slope)
    return times, ordered, slope, test


def ar1(generator, size, rho):
    value = generator.gauss(0, 1)
    values = []
    for _ in range(size):
        value = rho * value + generator.gauss(0, math.sqrt(1 - rho * rho))
        values.append(value)
    return values


@settings(max_examples=200)
@given(series)
def test_fenwick_s_matches_brute_force(values):
    assert kendall_s(values) == brute_force_s(values)


@given(series)
def test_s_is_antisymmetric_under_negation(values):
    assert kendall_s([-value for value in values]) == -kendall_s(values)


@given(series, st.integers(min_value=-100, max_value=100), st.integers(min_value=1, max_value=9))
def test_s_is_invariant_under_monotone_transform(values, shift, factor):
    assert kendall_s([value * factor + shift for value in values]) == kendall_s(values)


@given(series)
def test_average_ranks_sum_is_preserved(values):
    n = len(values)
    assert sum(average_ranks(values)) == pytest.approx(n * (n + 1) / 2)


@given(st.lists(st.floats(min_value=-50, max_value=50), min_size=3, max_size=25))
def test_sen_slope_matches_reference_median(values):
    times = [float(index) for index in range(len(values))]
    reference = median((b - a) / (j - i) for (i, a), (j, b) in itertools.combinations(enumerate(values), 2))
    assert median_of_sorted(pairwise_slopes(times, values)) == pytest.approx(reference, abs=1e-9)


@given(
    st.floats(min_value=-5, max_value=5),
    st.floats(min_value=-100, max_value=100),
    st.integers(min_value=3, max_value=40),
)
def test_sen_slope_recovers_exact_line(slope, intercept, size):
    times = [float(index) for index in range(size)]
    values = [intercept + slope * moment for moment in times]
    assert median_of_sorted(pairwise_slopes(times, values)) == pytest.approx(slope, abs=1e-6)


@given(st.lists(st.integers(min_value=-20, max_value=20), min_size=10, max_size=30))
def test_interval_contains_the_estimate(values):
    _, ordered, slope, test = fit([float(value) for value in values])
    lower, upper = sen_interval(ordered, pair_count(len(values)), test.variance, 0.95)
    assert lower <= slope <= upper


@given(st.lists(st.integers(min_value=-20, max_value=20), min_size=10, max_size=30))
def test_wider_confidence_never_narrows_the_interval(values):
    _, ordered, _, test = fit([float(value) for value in values])
    total = pair_count(len(values))
    narrow = sen_interval(ordered, total, test.variance, 0.8)
    wide = sen_interval(ordered, total, test.variance, 0.99)
    assert wide[0] <= narrow[0] and narrow[1] <= wide[1]


@given(st.lists(st.integers(min_value=-20, max_value=20), min_size=4, max_size=40))
def test_p_value_is_a_probability_and_inflation_is_conservative(values):
    _, _, _, test = fit([float(value) for value in values])
    assert 0 <= test.p_value <= 1
    assert test.variance_inflation >= 1


def test_tie_corrected_variance_reference_value():
    assert tied_variance([1, 2, 2, 3, 3, 3]) == pytest.approx((6 * 5 * 17 - (2 * 1 * 9 + 3 * 2 * 11)) / 18)


def test_mann_kendall_reference_values():
    times = [float(index) for index in range(10)]
    values = [float(index) for index in range(10)]
    result = mann_kendall(times, values, 0.0)
    assert result.s == 45
    assert result.variance / result.variance_inflation == pytest.approx(125.0)


def test_constant_series_has_no_trend():
    _, _, slope, test = fit([5.0] * 12)
    assert slope == 0
    assert (test.s, test.z, test.p_value) == (0, 0.0, 1.0)


def test_rejects_unsorted_times():
    with pytest.raises(ValueError, match="strictly increasing"):
        pairwise_slopes([0.0, 2.0, 1.0], [1.0, 2.0, 3.0])


def test_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        mann_kendall([0.0, 1.0], [1.0], 0.0)


def test_order_statistic_interpolates_and_clamps():
    ordered = [1.0, 2.0, 4.0]
    assert order_statistic(ordered, 2.5) == pytest.approx(3.0)
    assert order_statistic(ordered, -5) == 1.0
    assert order_statistic(ordered, 99) == 4.0


def test_pair_sampling_is_reproducible_and_bounded():
    generator = random.Random(1)
    values = [generator.gauss(0, 1) for _ in range(200)]
    times = [float(index) for index in range(200)]
    first = pairwise_slopes(times, values, max_pairs=500, seed=7)
    assert first == pairwise_slopes(times, values, max_pairs=500, seed=7)
    assert first != pairwise_slopes(times, values, max_pairs=500, seed=8)
    assert len(first) == 500


def test_sampled_slope_is_close_to_exact():
    generator = random.Random(3)
    times = [float(index) for index in range(300)]
    values = [0.02 * moment + generator.gauss(0, 0.5) for moment in times]
    exact = median_of_sorted(pairwise_slopes(times, values))
    sampled = median_of_sorted(pairwise_slopes(times, values, max_pairs=5000, seed=1))
    assert sampled == pytest.approx(exact, abs=0.001)


@pytest.mark.statistical
def test_false_positive_rate_on_white_noise_is_near_nominal():
    generator = random.Random(2026)
    rejections = sum(fit([generator.gauss(0, 1) for _ in range(40)])[3].p_value < 0.05 for _ in range(SIMULATIONS))
    assert 0.02 <= rejections / SIMULATIONS <= 0.09


@pytest.mark.statistical
def test_interval_coverage_on_linear_signal_is_near_nominal():
    generator = random.Random(2027)
    true_slope = -0.05
    covered = 0
    for _ in range(SIMULATIONS):
        values = [true_slope * index + generator.gauss(0, 1) for index in range(40)]
        _, ordered, _, test = fit(values)
        lower, upper = sen_interval(ordered, pair_count(40), test.variance, 0.95)
        covered += lower <= true_slope <= upper
    assert 0.90 <= covered / SIMULATIONS <= 0.995


@pytest.mark.statistical
def test_autocorrelation_correction_reduces_false_positives():
    generator = random.Random(2028)
    naive = corrected = 0
    for _ in range(SIMULATIONS):
        values = ar1(generator, 60, 0.7)
        times = [float(index) for index in range(60)]
        slope = median_of_sorted(pairwise_slopes(times, values))
        s = kendall_s(values)
        naive_z = (abs(s) - 1) / math.sqrt(tied_variance(values)) if s else 0.0
        naive += math.erfc(naive_z / math.sqrt(2)) < 0.05
        corrected += mann_kendall(times, values, slope).p_value < 0.05
    assert naive / SIMULATIONS > 0.25
    assert corrected < naive * 0.75


def test_inflation_exceeds_one_for_strong_autocorrelation():
    values = ar1(random.Random(11), 120, 0.9)
    times = [float(index) for index in range(120)]
    slope = median_of_sorted(pairwise_slopes(times, values))
    assert variance_inflation(times, values, slope) > 1.5
