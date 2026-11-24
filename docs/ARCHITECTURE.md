# Architecture

This page covers why each module exists, how to run the tests, and how the repository is laid out.

Why each layer exists:

| Module | Responsibility |
|---|---|
| `readers/` | The only code that touches `/sys`. Every reader takes a sysfs root, so tests run against fake machines, not the laptop running them. |
| `readers/power_supply.py` | Turns each vendor's `uevent` into typed values and applies firmware quirks (such as a cycle count of 0) in one place. |
| `readers/thermal.py` | Reads heat separately: it comes from a different subsystem than the battery, and may be missing even when the battery is fine. |
| `readers/dmi.py` | Keeps identity separate, so one log can hold several machines without mixing them up. |
| `models.py` | Frozen dataclasses: the one contract every layer shares. A sample can't change after it's read. |
| `storage/` | An interface in front of CSV, so a SQLite backend can replace it without touching readers or analysis. |
| `analysis/summary.py` | Pure functions over samples, so every number `show` prints is testable without sysfs or files. |
| `analysis/robust.py` | Generic rank statistics: Kendall S, Mann-Kendall, Hamed-Rao and Theil-Sen. Knows nothing about batteries. |
| `analysis/trend.py` | Applies those statistics to daily health and projects a threshold date. See [Statistical methods](methods.md). |
| `simulation/` | Seeded synthetic logs for validating the estimators. Always labelled `SYNTHETIC-<seed>`. |
| `cli/app.py` | The only layer that knows about arguments, default paths and exit codes. |
| `cli/render.py` | Turns results into terminal text and sanitizes untrusted strings. |
| `collect.py` | Keeps existing cron lines working. |

## Recommended architecture

battery-lab is a command-line tool with no client/server split, so it has no `frontend/` or
`backend/`. Dependencies point inward: `cli` depends on `analysis`, `storage` and `readers`, and all
of them depend on `models`. Keep sampling short-lived and scheduled by cron or a systemd timer
rather than adding a daemon. CSV remains the default store. For larger logs, implement the
`SampleStore` protocol over the optional schema in `db/schema.sql`.

## Development

```sh
pip install --require-hashes --only-binary=:all: -r requirements/dev.lock
pytest --hypothesis-seed=2026
ruff check battery_lab collect.py scripts tests
mypy
scripts/generate_test_report.sh python3
```

CI (`.github/workflows/ci.yml`) runs lint, strict typing, tests and a dependency audit on Python
3.11 through 3.14 for every push and pull request.

## Layout

```
battery-lab/
├── .github/                 # CI workflow and Dependabot
├── battery_lab/
│   ├── __init__.py          # version, public API
│   ├── __main__.py          # python -m battery_lab
│   ├── models.py            # frozen dataclasses
│   ├── analysis/            # summary, trend, robust statistics
│   ├── cli/                 # app (commands), render (output)
│   ├── readers/             # power_supply, thermal, dmi
│   ├── simulation/          # seeded synthetic logs
│   └── storage/             # SampleStore interface, CsvStore
├── db/schema.sql            # optional SQLite schema
├── docs/                    # documentation, starting at docs/README.md
├── reports/                 # committed test and validation output
├── requirements/            # hash-locked development tools
├── scripts/                 # test report and estimator validation
├── tests/                   # unit, property, statistical and security tests
├── collect.py               # compatibility shim for cron
└── data/                    # battery.csv is written here (gitignored)
```

---

Next: [Back to the project README](../README.md)

[Documentation index](README.md)
