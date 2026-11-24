#!/usr/bin/env python3
# Compatibility shim so existing cron lines keep working; the code lives in battery_lab/.
import sys

from battery_lab.cli import main

LEGACY_FLAGS = {"--json": "json", "--show": "show"}


def translate(argv: list[str]) -> list[str]:
    return [LEGACY_FLAGS.get(arg, arg) for arg in argv] or ["collect"]


if __name__ == "__main__":
    sys.exit(main(translate(sys.argv[1:])))
