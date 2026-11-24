#!/usr/bin/env bash
# Runs the suite on one interpreter and writes the real pytest output to reports/tests/.
set -euo pipefail

python_bin="${1:-python3}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="$("$python_bin" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
report="$repo_root/reports/tests/pytest-py$version.txt"
output="$(mktemp)"
trap 'rm -f "$output"' EXIT

cd "$repo_root"
set +e
COVERAGE_FILE="$output.coverage" PYTHONDONTWRITEBYTECODE=1 "$python_bin" -m pytest \
  -v --no-header --color=no -p no:cacheprovider --hypothesis-seed=2026 \
  --cov=battery_lab --cov-branch --cov-report=term >"$output" 2>&1
status=$?
set -e
rm -f "$output.coverage"

{
  echo "battery-lab test report"
  echo "generated_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "base_commit: $(git rev-parse --short HEAD)"
  echo "python: $("$python_bin" -c 'import platform; print(platform.python_version())')"
  echo "pytest: $("$python_bin" -c 'import pytest; print(pytest.__version__)')"
  echo "hypothesis_seed: 2026"
  echo "exit_code: $status"
  echo
  cat "$output"
} >"$report"

tail -n 1 "$output"
exit "$status"
