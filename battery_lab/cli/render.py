# Terminal rendering. Every value that originates from firmware or a log file passes through safe_text.
import unicodedata
from collections.abc import Sequence

from battery_lab.analysis.summary import UNKNOWN_STATUS
from battery_lab.analysis.trend import HealthTrend
from battery_lab.models import BatterySample, BatterySummary

UNSAFE_CATEGORIES = ("C", "Zl", "Zp")


def safe_text(value: str) -> str:
    return "".join("?" if unicodedata.category(char).startswith(UNSAFE_CATEGORIES) else char for char in value)


def status_label(status: str | None) -> str:
    return safe_text(status or UNKNOWN_STATUS)


def render_sample(sample: BatterySample, destination: object) -> str:
    return (
        f"{safe_text(sample.battery)}  {status_label(sample.status)}  {percent(sample.capacity)}  "
        f"health {percent(sample.health_pct, 2)}  temp {temperature(sample.temp_c)}  -> {destination}"
    )


def render_summary(summary: BatterySummary) -> list[str]:
    first, last = summary.first, summary.last
    identity = ", ".join(safe_text(value) for value in (last.model_name, last.manufacturer, last.technology) if value)
    heading = f"{safe_text(summary.machine_id)} / {safe_text(summary.battery)}"
    lines = [heading + (f"  ({identity})" if identity else "")]
    lines.append(f"  samples        {len(summary.samples)}")
    lines.append(f"  first          {first.timestamp.isoformat(timespec='seconds')}")
    lines.append(f"  last           {last.timestamp.isoformat(timespec='seconds')}")
    lines.append(f"  span           {format_duration(summary.span_seconds)}")

    health = summary.health
    if health is None:
        lines.append("  health         n/a (no full/design capacity readings)")
    else:
        lines.append(
            f"  health         {health.first_pct:.2f}% -> {health.last_pct:.2f}%  (delta {health.delta_pp:+.2f} pp)"
        )
        lines.append(f"  full capacity  first: {capacity_text(health.first)}")
        lines.append(f"                 last:  {capacity_text(health.last)}")

    cycles = summary.cycle_count
    lines.append(f"  cycle count    {cycles if cycles is not None else 'not reported by firmware'}")
    lines.append(
        f"  latest         {status_label(last.status)}, {percent(last.capacity)}, "
        f"{scaled(last.voltage_now, 1_000_000, 'V', 3)}, {scaled(last.current_now, 1000, 'mA', 1)}, "
        f"{temperature(last.temp_c)}"
    )

    stats = summary.temperature
    if stats is None:
        lines.append("  temp_c         not recorded")
    else:
        plural = "" if stats.count == 1 else "s"
        lines.append(
            f"  temp_c         min {stats.minimum:.1f} / median {stats.median:.1f} / max {stats.maximum:.1f} °C  "
            f"({stats.count} sample{plural})"
        )

    timeline = summary.timeline
    lines.extend(["", "  time by status"])
    if timeline.tracked_seconds:
        labelled = [(status_label(status), seconds) for status, seconds in timeline.durations.items()]
        width = max(len(label) for label, _ in labelled)
        for label, seconds in sorted(labelled, key=lambda item: -item[1]):
            share = seconds / timeline.tracked_seconds * 100
            lines.append(f"    {label:<{width}}  {format_duration(seconds):>12}  {share:5.1f}%")
    else:
        lines.append("    no tracked intervals yet")
    lines.append(f"  untracked gaps {format_duration(timeline.gap_seconds)}")
    lines.append(f"  status changes {timeline.change_count}")
    for (before, after), count in sorted(timeline.changes.items(), key=lambda item: -item[1]):
        lines.append(f"    {status_label(before)} -> {status_label(after)}: {count}")
    return lines


def render_trend(machine: str, battery: str, trend: HealthTrend | None, day_count: int, minimum: int) -> list[str]:
    heading = f"{safe_text(machine)} / {safe_text(battery)}"
    if trend is None:
        return [heading, f"  insufficient data: {day_count} measured day(s), at least {minimum} required"]
    test = trend.mann_kendall
    level = round(trend.confidence * 100, 2)
    lines = [
        heading,
        f"  measured days  {trend.days_observed} ({trend.first_day} to {trend.last_day})",
        f"  verdict        {trend.verdict}",
        f"  Sen slope      {trend.slope_pp_per_year:+.3f} pp/year "
        f"({level:g}% CI {trend.slope_lower_pp_per_year:+.3f} to {trend.slope_upper_pp_per_year:+.3f})",
        f"  Mann-Kendall   S={test.s} z={test.z:.3f} p={test.p_value:.4g} "
        f"(variance inflation {test.variance_inflation:.2f})",
        f"  slope method   {'exact, all pairs' if trend.exact else f'sampled pairs, seed {trend.seed}'}",
        f"  fitted health  {trend.fitted_last_pct:.2f}% on {trend.last_day}",
    ]
    crossing = trend.crossing
    if crossing is not None:
        lines.append(
            f"  projection     {trend.threshold_pct:g}% around {crossing.estimate} "
            f"(range {crossing.earliest} to {crossing.latest}; linear extrapolation, not a measurement)"
        )
    return lines


def format_duration(seconds: float) -> str:
    total = round(seconds)
    if total < 60:
        return f"{total}s"
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def percent(value: float | None, digits: int = 0) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}%"


def temperature(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f} °C"


def scaled(value: int | None, divisor: int, unit: str, digits: int = 0) -> str:
    return "n/a" if value is None else f"{value / divisor:.{digits}f} {unit}"


def capacity_text(sample: BatterySample) -> str:
    if sample.charge_full is not None:
        return f"{scaled(sample.charge_full, 1000, 'mAh')} of {scaled(sample.charge_full_design, 1000, 'mAh')} design"
    if sample.energy_full is not None:
        return f"{scaled(sample.energy_full, 1000, 'mWh')} of {scaled(sample.energy_full_design, 1000, 'mWh')} design"
    return "n/a"


def join_blocks(title: str, blocks: Sequence[list[str]]) -> str:
    lines = [title]
    for block in blocks:
        lines.append("")
        lines.extend(block)
    return "\n".join(lines)
