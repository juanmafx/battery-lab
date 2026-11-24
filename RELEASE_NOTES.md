# battery-lab 1.0.1 release notes

Released on 2026-11-24.

This is a documentation-only patch release. It corrects the release notes, changelog links,
security audit and committed test reports so that they describe the published 1.0.0 release and
the rewritten repository history accurately. There is no change in code behaviour.

## Upgrade

No migration is needed from 1.0.0. When upgrading from 0.1.0, note the 1.0.0 breaking changes:

- Python 3.11 or newer is required.
- `battery_lab.cli` is now a package. `battery_lab.cli.main` and the console script are unchanged.
- Text cells that could be read as spreadsheet formulas gain a leading `'` in the CSV. Rows written
  by 0.1.0 are not escaped, so review old logs before opening them in a spreadsheet. Consider
  `chmod 600` on existing logs.

See [CHANGELOG.md](CHANGELOG.md) for the full list.
