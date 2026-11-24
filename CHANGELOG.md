# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - Unreleased

### Added

- `trend` command: daily medians, Theil-Sen slope, Mann-Kendall test with tie and Hamed-Rao
  corrections, rank-based confidence interval and a linear threshold projection.
- `simulate` command: seeded synthetic logs, always labelled and never written over existing files.
- Optional normalized SQLite schema in `db/schema.sql`.
- Property-based, statistical, security and schema tests, with committed reports from real runs.
- `scripts/validate_estimators.py`, `docs/methods.md`, `SECURITY.md` and `docs/SECURITY_AUDIT.md`.

### Changed

- **Breaking:** Python 3.11 or newer is required.
- **Breaking:** `battery_lab.cli` is now a package.
- **Breaking:** text cells that could be read as spreadsheet formulas are escaped in the CSV.
- CI pins actions to commits, installs hash-locked tools and runs lint, types, tests and an audit.

### Fixed

- `trend` takes its direction from the Mann-Kendall statistic, so a significant decline with a
  zero median slope is no longer labelled `rising`.
- Migrating a symlinked log keeps the link and updates its target.

### Security

- New logs are private (`0600`), appends are locked and migration uses a unique staging file.
- `simulate` creates its file exclusively and never writes through a symlink.
- A row truncated inside a quoted cell no longer swallows later rows.
- Terminal output strips control characters and Unicode line separators.
- Oversized integers, out-of-range timestamps, closed pipes and non-UTF-8 terminals are handled
  without a traceback.
- Removed personal contact details and a real device identifier from the current tree.

## [0.1.0] - 2026-09-14

### Added

- Initial release.
- Read-only sampling of `/sys/class/power_supply/BAT*/uevent`: one sample per run, never writes
  to the kernel, never needs `sudo`.
- Thermal zone logging: the hottest readable zone under `/sys/class/thermal` is recorded as
  `temp_c`.
- CSV storage with header validation: older headers are migrated in place, unrecognized headers
  are refused and the file is left untouched.
- Summary analysis: health delta, time-by-status breakdown and gap detection.
- 58 tests with synthetic sysfs fixtures: Dell, HP with `energy_*` fields, dual-battery ThinkPad,
  desktop without a battery, and a malformed `uevent`.

[Unreleased]: https://github.com/juanmafx/battery-lab/compare/v0.1.0...HEAD
[1.0.0]: https://github.com/juanmafx/battery-lab/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/juanmafx/battery-lab/releases/tag/v0.1.0
