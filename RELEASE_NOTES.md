# battery-lab 1.0.0 release notes

Status: prepared, not yet tagged or published.

## Highlights

- **Trend analysis.** `battery-lab trend` estimates capacity fade using daily medians, the
  Theil-Sen slope, a Mann-Kendall test with Hamed-Rao correction, and a confidence interval.
- **Reproducible simulation.** `battery-lab simulate` creates seeded, clearly labelled synthetic logs.
- **Hardened storage and output.** Private file permissions, formula-injection protection, locked
  appends, safe migration and sanitized terminal output.
- **Optional SQL schema.** A normalized SQLite schema in `db/schema.sql`.
- **Stronger quality gates.** Property-based and statistical tests, strict typing, and a pinned CI.

## Breaking changes

- Python 3.11 or newer is required. Python 3.9 and 3.10 are end-of-life.
- `battery_lab.cli` is now a package. `battery_lab.cli.main` and the console script are unchanged.
- Text cells starting with `=`, `+`, `-`, `@`, tab, carriage return or `'` gain a leading `'` in the
  CSV. battery-lab removes it on read, but external tools will see it.

## Upgrade

Existing logs remain readable and no migration is needed. Existing cron lines keep working,
provided the interpreter they use is Python 3.11 or newer. Consider `chmod 600` on existing logs.

See [CHANGELOG.md](CHANGELOG.md) for the full list.
