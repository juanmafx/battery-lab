import pytest

from battery_lab.analysis.summary import (
    UNKNOWN_STATUS,
    gap_limit,
    health_delta,
    status_timeline,
    summarize,
    temperature_stats,
)


def test_health_delta_spans_first_and_last_measured_samples(make_sample):
    samples = [
        make_sample(0, charge_full=None),
        make_sample(5, charge_full=2956000),
        make_sample(10, charge_full=2920498),
        make_sample(15, charge_full=None),
    ]
    delta = health_delta(samples)
    assert delta.first is samples[1]
    assert delta.last is samples[2]
    assert (delta.first_pct, delta.last_pct) == (83.64, 82.64)
    assert delta.delta_pp == pytest.approx(-1.0)


def test_health_delta_orders_by_time(make_sample):
    late, early = make_sample(10, charge_full=2900000), make_sample(0)
    delta = health_delta([late, early])
    assert delta.first is early
    assert delta.last is late


def test_health_delta_is_none_without_capacity_readings(make_sample):
    assert health_delta([make_sample(charge_full=None)]) is None
    assert health_delta([]) is None


def test_interval_is_credited_to_the_earlier_status(make_sample):
    samples = [
        make_sample(0, status="Not charging"),
        make_sample(5, status="Discharging"),
        make_sample(10, status="Discharging"),
        make_sample(15, status="Not charging"),
    ]
    timeline = status_timeline(samples)
    assert timeline.durations == {"Not charging": 300.0, "Discharging": 600.0}
    assert timeline.changes == {("Not charging", "Discharging"): 1, ("Discharging", "Not charging"): 1}
    assert timeline.change_count == 2
    assert timeline.gaps == ()


def test_long_interval_becomes_a_gap_instead_of_status_time(make_sample):
    samples = [make_sample(minutes, status="Discharging") for minutes in (0, 5, 10, 15, 120, 125)]
    timeline = status_timeline(samples)
    [gap] = timeline.gaps
    assert (gap.start, gap.end) == (samples[3].timestamp, samples[4].timestamp)
    assert timeline.gap_seconds == 105 * 60
    assert timeline.durations == {"Discharging": 4 * 300.0}


def test_status_change_across_a_gap_is_not_counted(make_sample):
    samples = [
        make_sample(0, status="Charging"),
        make_sample(5, status="Charging"),
        make_sample(10, status="Charging"),
        make_sample(200, status="Discharging"),
    ]
    timeline = status_timeline(samples)
    assert timeline.changes == {}
    assert len(timeline.gaps) == 1


def test_gap_limit_is_factor_times_median_of_positive_intervals():
    assert gap_limit([300.0, 300.0, 0.0, 600.0]) == 900.0
    assert gap_limit([300.0, 600.0], factor=2) == 900.0
    assert gap_limit([0.0]) is None
    assert gap_limit([]) is None


def test_single_sample_and_duplicate_timestamps_track_nothing(make_sample):
    assert status_timeline([make_sample(0)]).tracked_seconds == 0
    duplicate = status_timeline([make_sample(0), make_sample(0)])
    assert duplicate.durations == {}
    assert duplicate.gaps == ()


def test_missing_status_is_labelled_unknown(make_sample):
    timeline = status_timeline([make_sample(0, status=None), make_sample(5)])
    assert timeline.durations == {UNKNOWN_STATUS: 300.0}
    assert timeline.changes == {(UNKNOWN_STATUS, "Not charging"): 1}


def test_temperature_stats_skip_missing_readings(make_sample):
    samples = [make_sample(0, temp_c=41.0), make_sample(5, temp_c=None), make_sample(10, temp_c=93.0), make_sample(15, temp_c=60.5)]
    stats = temperature_stats(samples)
    assert (stats.minimum, stats.median, stats.maximum, stats.count) == (41.0, 60.5, 93.0, 3)
    assert temperature_stats([make_sample(temp_c=None)]) is None


def test_summarize_groups_by_machine_and_battery_in_time_order(make_sample):
    samples = [
        make_sample(10, battery="BAT1"),
        make_sample(5),
        make_sample(0),
        make_sample(0, machine_id="OTHER", cycle_count=12),
    ]
    summaries = summarize(samples)
    assert [(s.machine_id, s.battery, len(s.samples)) for s in summaries] == [
        ("TEST-MACHINE", "BAT1", 1),
        ("TEST-MACHINE", "BAT0", 2),
        ("OTHER", "BAT0", 1),
    ]
    bat0 = summaries[1]
    assert bat0.first is samples[2]
    assert bat0.last is samples[1]
    assert bat0.span_seconds == 300.0
    assert bat0.cycle_count is None
    assert summaries[2].cycle_count == 12
