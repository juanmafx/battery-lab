import argparse
import json
import math
import os
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from battery_lab import __version__, collect_samples
from battery_lab.analysis.summary import summarize
from battery_lab.analysis.trend import DEFAULT_SEED, DEFAULT_THRESHOLD_PCT, MIN_TREND_DAYS, daily_health, health_trend
from battery_lab.cli.render import join_blocks, render_sample, render_summary, render_trend
from battery_lab.models import BatterySample
from battery_lab.simulation.synthetic import simulate_samples
from battery_lab.storage import SampleStore, StorageError
from battery_lab.storage.csv_store import CsvStore


def default_home() -> Path:
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "pyproject.toml").is_file():
        return checkout
    data_home = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data_home) / "battery-lab"


def finite_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"not a number: {text}") from error
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError(f"not a finite number: {text}")
    return value


def non_negative_float(text: str) -> float:
    value = finite_float(text)
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be zero or greater: {text}")
    return value


def percentage(text: str) -> float:
    value = finite_float(text)
    if not 0 < value <= 100:
        raise argparse.ArgumentTypeError(f"must be in (0, 100]: {text}")
    return value


def confidence_level(text: str) -> float:
    value = finite_float(text)
    if not 0 < value < 1:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1: {text}")
    return value


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"not an integer: {text}") from error
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be 1 or greater: {text}")
    return value


def build_parser() -> argparse.ArgumentParser:
    home = default_home()
    sampling = argparse.ArgumentParser(add_help=False)
    sampling.add_argument(
        "--sysfs-root", type=Path, default=Path("/sys"), metavar="PATH", help="sysfs tree to read (default: %(default)s)"
    )
    sampling.add_argument(
        "--env-file", type=Path, default=home / ".env", metavar="PATH", help="file holding MACHINE_ID (default: %(default)s)"
    )
    storage = argparse.ArgumentParser(add_help=False)
    storage.add_argument(
        "--data", type=Path, default=home / "data" / "battery.csv", metavar="PATH", help="CSV logbook (default: %(default)s)"
    )

    parser = argparse.ArgumentParser(prog="battery-lab", description="Read-only battery health logbook. One run, one sample.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    commands.required = True
    commands.add_parser("collect", parents=[sampling, storage], help="take one sample and append it to the CSV")
    commands.add_parser("show", parents=[storage], help="summarize the CSV")
    commands.add_parser("json", parents=[sampling], help="print one sample as JSON; writes nothing")

    trend = commands.add_parser("trend", parents=[storage], help="estimate the long-term health trend from the CSV")
    trend.add_argument("--threshold", type=percentage, default=DEFAULT_THRESHOLD_PCT, metavar="PCT", help="health level to project (default: %(default)s)")
    trend.add_argument("--confidence", type=confidence_level, default=0.95, metavar="LEVEL", help="confidence level (default: %(default)s)")
    trend.add_argument("--seed", type=int, default=DEFAULT_SEED, help="seed for pair sampling on very long logs (default: %(default)s)")
    trend.add_argument("--json", action="store_true", help="print machine-readable output")

    simulate = commands.add_parser("simulate", help="write a labelled synthetic log to a new file")
    simulate.add_argument("--output", type=Path, required=True, metavar="PATH", help="new CSV to create; an existing file is refused")
    simulate.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed (default: %(default)s)")
    simulate.add_argument("--days", type=positive_int, default=365, help="days to simulate (default: %(default)s)")
    simulate.add_argument("--start-health", type=percentage, default=90.0, metavar="PCT", help="initial health (default: %(default)s)")
    simulate.add_argument("--fade", type=finite_float, default=4.0, metavar="PP", help="health loss in pp/year (default: %(default)s)")
    simulate.add_argument("--noise", type=non_negative_float, default=0.15, metavar="PP", help="reading noise in pp (default: %(default)s)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "show":
            return show(CsvStore(args.data), args.data)
        if args.command == "trend":
            return trend(CsvStore(args.data), args)
        if args.command == "simulate":
            return simulate(args)
        samples = collect_samples(args.sysfs_root, args.env_file)
        if args.command == "json":
            print(json.dumps([sample.to_record() for sample in samples], indent=2))
            return 0 if samples else 1
        return collect(samples, CsvStore(args.data), args.data, args.sysfs_root)
    except StorageError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def collect(samples: list[BatterySample], store: SampleStore, destination: Path, sysfs_root: Path) -> int:
    if not samples:
        print(f"error: no battery found under {sysfs_root / 'class' / 'power_supply'}", file=sys.stderr)
        return 1
    store.append(samples)
    for sample in samples:
        print(render_sample(sample, destination))
    return 0


def show(store: SampleStore, source: Path) -> int:
    summaries = summarize(store.load())
    if not summaries:
        print(f"no samples in {source}")
        return 1
    print(join_blocks(f"battery-lab summary: {source}", [render_summary(summary) for summary in summaries]))
    return 0


def trend(store: SampleStore, args: argparse.Namespace) -> int:
    summaries = summarize(store.load())
    if not summaries:
        print(f"no samples in {args.data}")
        return 1
    results = [
        (
            summary,
            health_trend(summary.samples, threshold_pct=args.threshold, confidence=args.confidence, seed=args.seed),
        )
        for summary in summaries
    ]
    if args.json:
        records = [
            {
                "machine_id": summary.machine_id,
                "battery": summary.battery,
                "measured_days": len(daily_health(summary.samples)),
                "trend": asdict(result) if result is not None else None,
            }
            for summary, result in results
        ]
        print(json.dumps(records, indent=2, default=str))
        return 0
    blocks = [
        render_trend(summary.machine_id, summary.battery, result, len(daily_health(summary.samples)), MIN_TREND_DAYS)
        for summary, result in results
    ]
    print(join_blocks(f"battery-lab trend: {args.data}", blocks))
    return 0


def simulate(args: argparse.Namespace) -> int:
    if args.output.exists():
        print(f"error: {args.output} already exists; simulate only creates new files", file=sys.stderr)
        return 1
    samples = simulate_samples(
        seed=args.seed,
        days=args.days,
        start_health_pct=args.start_health,
        fade_pp_per_year=args.fade,
        noise_pp=args.noise,
    )
    CsvStore(args.output).append(samples)
    print(f"wrote {len(samples)} synthetic samples for {samples[0].machine_id} -> {args.output}")
    return 0
