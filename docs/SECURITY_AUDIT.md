# Security audit

Scope: the full tree of version 1.0.0 on branch `modernize/2026`, reviewed in November 2026.
This is a self-review with the tools listed below, not an independent third-party audit.

## Method

- Manual review of every module, with attention to input handling, file operations and output.
- `ruff` with the `S` (bandit) rule set, and `mypy --strict`.
- `pip-audit` against the hash-locked development dependencies, which reported no known
  vulnerabilities at review time. There are no runtime dependencies.
- Regression tests for each fix in `tests/test_security.py`.

## Fixed

| Severity | Area | Issue | Fix |
|---|---|---|---|
| Medium | Privacy | Logs holding serial numbers were created with default, often world-readable, permissions | New logs use `0600`, new directories `0700` |
| Medium | CSV | Firmware or `MACHINE_ID` strings could be interpreted as spreadsheet formulas | Text cells are escaped on write and restored on read |
| Medium | Terminal | Firmware or log strings could carry escape sequences into `show` output | Control and format characters are replaced before printing |
| Medium | Filesystem | Migration used a predictable staging filename and followed symlinks | Staging uses a unique `mkstemp` file, then an atomic replace |
| Low | Integrity | Concurrent runs could interleave rows or write two headers | Appends take an exclusive lock |
| Low | Integrity | A truncated last row corrupted the next append | The missing line ending is repaired first |
| Low | Availability | Oversized integers, deep JSON, extreme dates or invalid encodings could crash a run | Handled as null values or a clean error |
| Low | Availability | Attribute reads were unbounded | Reads are capped at 64 KiB |
| Low | Privacy | A real device identifier appeared in a test and a figure | Replaced with synthetic values |
| Low | Privacy | Personal contact details were published in the README | Removed from the current tree |
| Low | Supply chain | CI used mutable action tags and unpinned tools on end-of-life Python 3.9 | Actions pinned to commits, tools hash-locked, Python 3.11 to 3.14 |

## Open

| Severity | Issue | Required action |
|---|---|---|
| Low | Personal contact details and a device identifier remain in git history and on the default branch until this work is merged | Owner decides whether to rewrite history. Treat them as already public |
| Info | Logs created by earlier versions keep their existing permissions | Run `chmod 600` on existing logs |
| Info | The `json` command and CSV include the battery serial number by design | Review before sharing |

No committed secrets, private keys, dependency folders or build artifacts were found in the tree.
