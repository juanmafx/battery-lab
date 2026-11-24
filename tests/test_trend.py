import json
from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from battery_lab.analysis.trend import MIN_TREND_DAYS, daily_health, health_trend, project_crossing
from battery_lab.cli import main
from battery_lab.models import BatterySample
from battery_lab.simulation.synthetic import simulate_samples
from battery_lab.storage.csv_store import CsvStore

DESIGN = 1_000_000
START = datetime(2026, 1, 1, 12, tzinfo=UTC)


def daily_samples(values):
    return [
        BatterySample(
            machine_id="M",
            timestamp=START + timedelta(days=index),
            battery="BAT0",
            charge_full=round(DESIGN * value / 100),
            charge_full_design=DESIGN,
        )
        for index, value in enumerate(values)
    ]


def test_daily_health_takes_the_median_of_each_utc_day():
    samples = daily_samples([80.0, 90.0])
    extra = BatterySample("M", START + timedelta(hours=1), "BAT0", charge_full=700_000, charge_full_design=DESIGN)
    other = BatterySample("M", START + timedelta(hours=2), "BAT0", charge_full=None)
    assert daily_health([*samples, extra, other]) == [(date(2026, 1, 1), 75.0), (date(2026, 1, 2), 90.0)]


def test_trend_requires_minimum_days():
    assert health_trend(daily_samples([80.0] * (MIN_TREND_DAYS - 1))) is None
    assert health_trend(daily_samples([80.0] * MIN_TREND_DAYS)) is not None


def test_flat_series_reports_no_trend_and_no_projection():
    trend = health_trend(daily_samples([85.0] * 30))
    assert trend.verdict == "no statistically significant trend"
    assert trend.slope_pp_per_year == 0
    assert trend.crossing is None


def test_declining_series_recovers_slope_and_projects_threshold():
    samples = simulate_samples(seed=5, days=365, start_health_pct=90, fade_pp_per_year=6, noise_pp=0.05)
    trend = health_trend(samples, threshold_pct=70)
    assert trend.verdict == "declining"
    assert trend.exact is True
    assert trend.slope_lower_pp_per_year <= -6 <= trend.slope_upper_pp_per_year
    assert trend.slope_pp_per_year == pytest.approx(-6, abs=0.1)
    assert trend.crossing.earliest <= trend.crossing.estimate <= trend.crossing.latest
    assert trend.crossing.estimate.year in (2029, 2030)


def test_rising_series_is_not_projected():
    trend = health_trend(daily_samples([70.0 + index * 0.1 for index in range(40)]))
    assert trend.verdict == "rising"
    assert trend.crossing is None


def test_battery_already_below_threshold_has_no_projection():
    trend = health_trend(daily_samples([65.0 - index * 0.1 for index in range(40)]), threshold_pct=70)
    assert trend.verdict == "declining"
    assert trend.crossing is None


def test_projection_beyond_horizon_is_withheld():
    assert project_crossing(date(2026, 1, 1), 90.0, 70.0, -0.01, -0.02, -0.001) is None


def test_sampled_trend_is_reproducible_for_a_seed():
    samples = simulate_samples(seed=9, days=120, fade_pp_per_year=5)
    first = health_trend(samples, seed=1, max_pairs=1000)
    assert first.exact is False
    assert first == health_trend(samples, seed=1, max_pairs=1000)


@settings(max_examples=25, deadline=None)
@given(st.integers(min_value=0, max_value=2**32), st.floats(min_value=2, max_value=10))
def test_estimated_fade_stays_near_truth(seed, fade):
    trend = health_trend(simulate_samples(seed=seed, days=365, fade_pp_per_year=fade, noise_pp=0.1))
    assert trend.slope_pp_per_year == pytest.approx(-fade, abs=0.25)


@given(st.integers(min_value=0, max_value=2**32))
def test_simulation_is_deterministic(seed):
    assert simulate_samples(seed, 3) == simulate_samples(seed, 3)


@pytest.mark.parametrize("arguments", [(1, 0), (1, 1, 90.0, 4.0, 0.1, 0)])
def test_simulation_rejects_empty_runs(arguments):
    with pytest.raises(ValueError, match="at least 1"):
        simulate_samples(*arguments)


def test_simulated_machine_is_always_labelled():
    assert {sample.machine_id for sample in simulate_samples(42, 2)} == {"SYNTHETIC-42"}


def test_cli_simulate_then_trend(tmp_path, capsys):
    data = tmp_path / "synthetic.csv"
    assert main(["simulate", "--output", str(data), "--seed", "3", "--days", "200", "--fade", "8", "--noise", "0.05"]) == 0
    assert main(["trend", "--data", str(data)]) == 0
    out = capsys.readouterr().out
    assert "SYNTHETIC-3 / BAT0" in out
    assert "declining" in out
    assert "not a measurement" in out


def test_cli_trend_json_is_valid(tmp_path, capsys):
    data = tmp_path / "synthetic.csv"
    main(["simulate", "--output", str(data), "--seed", "4", "--days", "60"])
    capsys.readouterr()
    assert main(["trend", "--data", str(data), "--json"]) == 0
    [record] = json.loads(capsys.readouterr().out)
    assert record["machine_id"] == "SYNTHETIC-4"
    assert record["measured_days"] == 60
    assert record["trend"]["mann_kendall"]["n"] == 60


def test_cli_trend_reports_insufficient_data(tmp_path, capsys, make_sample):
    data = tmp_path / "battery.csv"
    CsvStore(data).append([make_sample(0)])
    assert main(["trend", "--data", str(data)]) == 0
    assert "insufficient data: 1 measured day(s)" in capsys.readouterr().out


def test_cli_trend_without_samples_fails(tmp_path, capsys):
    assert main(["trend", "--data", str(tmp_path / "absent.csv")]) == 1
    assert "no samples" in capsys.readouterr().out


def test_simulate_refuses_to_touch_an_existing_log(tmp_path, capsys):
    data = tmp_path / "battery.csv"
    data.write_text("real data\n")
    assert main(["simulate", "--output", str(data)]) == 1
    assert data.read_text() == "real data\n"
    assert "already exists" in capsys.readouterr().err


@pytest.mark.parametrize(
    "arguments",
    [
        ["trend", "--confidence", "1.5"],
        ["trend", "--confidence", "nan"],
        ["trend", "--threshold", "0"],
        ["simulate", "--output", "x", "--days", "0"],
        ["simulate", "--output", "x", "--days", "many"],
        ["simulate", "--output", "x", "--noise", "-1"],
        ["simulate", "--output", "x", "--fade", "inf"],
        ["simulate", "--output", "x", "--fade", "fast"],
    ],
)
def test_cli_rejects_invalid_numbers(arguments):
    with pytest.raises(SystemExit) as exit_info:
        main(arguments)
    assert exit_info.value.code == 2
