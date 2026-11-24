# Security audit

Scope: the full tree of version 1.0.0 on branch `modernize/2026`, reviewed in November 2026.
This is a self-review with the tools listed below, not an independent third-party audit.

## Method

- Manual review of every module, with attention to input handling, file operations and output.
- `ruff` with the `S` (bandit) rule set, and `mypy --strict`.
- `pip-audit` against the hash-locked development dependencies, which reported no known
  vulnerabilities at review time. There are no runtime dependencies.
- `gitleaks` with redaction over the git history and the working tree, with no findings.
- Adversarial probes of storage, parsing and output, with regression tests in
  `tests/test_security.py`, `tests/test_readers.py` and `tests/test_trend.py`.

XSS, CSRF, authentication, 2FA and cryptography do not apply: battery-lab is a local command-line
tool with no web interface, accounts, network access or stored credentials.

## Fixed

| Severity | Area | Issue | Fix |
|---|---|---|---|
| Medium | Privacy | Logs holding serial numbers were created with default, often world-readable, permissions | New logs use `0600`, and every directory created for them `0700` |
| Medium | CSV | Firmware or `MACHINE_ID` strings could be interpreted as spreadsheet formulas | Text cells are escaped on write and restored on read |
| Medium | Terminal | Firmware or log strings could carry escape sequences into `show` output | Control and format characters are replaced before printing |
| Medium | Filesystem | Migration used a predictable staging filename and followed symlinks | Staging uses a unique `mkstemp` file, then an atomic replace |
| Medium | Filesystem | `simulate` could write through a dangling symlink at a predictable path | New files are created with `O_CREAT \| O_EXCL` |
| Medium | Integrity | A row truncated inside a quoted cell swallowed the rows appended after it | The open quote is closed before the next append |
| Medium | CI | The workflow was invalid YAML, so no job ran | The affected command is quoted |
| Low | Integrity | Migrating a symlinked log replaced the link with a regular file | The link target is rewritten and the link is kept |
| Low | Correctness | A significant decline with a zero median slope was labelled `rising` | The direction comes from the sign of the Mann-Kendall statistic |
| Low | Integrity | Concurrent runs could interleave rows or write two headers | Appends take an exclusive lock |
| Low | Integrity | A truncated last row corrupted the next append | The missing line ending is repaired first |
| Low | Availability | Oversized integers, deep JSON, extreme dates or invalid encodings could crash a run | Integers outside the signed 64-bit range and timestamps outside the UTC range are null; other cases are a clean error |
| Low | Availability | Output to a closed pipe or a non-UTF-8 terminal raised a traceback, and `simulate --days` was unbounded | Handled cleanly; `--days` is capped at 36,525 |
| Low | Parsing | Unicode line separators could inject `uevent` or `.env` fields and reach terminal output | Lines split on `\n` only, and separators are replaced in output |
| Low | Availability | Attribute reads were unbounded | Reads are capped at 64 KiB |
| Low | Privacy | A real device identifier appeared in a test and a figure | Replaced with synthetic values |
| Low | Privacy | Personal contact details were published in the README | Removed from the current tree |
| Low | Privacy | Personal contact details and a device identifier remained in git history | Resolved by the 2026-11-24 history rewrite. Treat them as already public, because they were published before it |
| Low | Supply chain | CI used mutable action tags and unpinned tools on end-of-life Python 3.9 | Actions pinned to commits, tools hash-locked, Python 3.11 to 3.14 |

## Open

| Severity | Issue | Required action |
|---|---|---|
| Low | Rows written by 0.1.0 are not escaped, so a formula-like cell in an old log stays live in a spreadsheet | Review old logs before opening them in a spreadsheet |
| Low | The private vulnerability reporting feature is disabled on the repository | Owner can enable it in the repository settings |
| Info | Logs created by earlier versions keep their existing permissions | Run `chmod 600` on existing logs |
| Info | The `json` command and CSV include the battery serial number by design | Review before sharing |

No committed secrets, private keys, dependency folders or build artifacts were found in the tree.
