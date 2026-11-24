# Install and use

This page covers installing battery-lab, its commands, cron, and where its files live.

## Install

Current version: **1.0.0**. Release notes are in [CHANGELOG.md](../CHANGELOG.md).

Python 3.11+. No runtime dependencies: standard library only.

From a checkout of this repository:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

The virtual environment matters on Ubuntu 23.04 and later, where the system `pip` refuses to
install packages (PEP 668). `pipx install --editable .` works too.

## Usage

```sh
battery-lab collect     # take one sample, append it to the CSV
battery-lab json        # print one sample as JSON to stdout; writes nothing
battery-lab show        # summarize the CSV
battery-lab trend       # estimate the long-term health trend
battery-lab simulate --output new.csv   # write a labelled synthetic log
```

`python -m battery_lab <command>` does the same without the console script.

| Situation | Where the CSV and `.env` live |
|---|---|
| Running from a checkout (`pip install -e .` or `collect.py`) | `data/battery.csv` and `.env` in the checkout |
| Installed any other way | `$XDG_DATA_HOME/battery-lab/`, usually `~/.local/share/battery-lab/` |
| `--data PATH` or `--env-file PATH` given | Wherever you point them |

**Installing both ways creates two separate logs:** a GitHub install stores data in
`~/.local/share/battery-lab/`, while a checkout install stores it in `data/`.

`--sysfs-root PATH` reads a different sysfs tree. The tests use it to simulate other machines.

`battery-lab show` prints one block per machine and battery:

- number of samples and time span
- `health_pct` first → last, with the delta in percentage points
- full capacity at the first and last sample (mAh or mWh)
- cycle count, or "not reported by firmware"
- latest status, charge %, voltage, current and temperature
- `temp_c` minimum, median and maximum across all samples
- time spent in each `STATUS`, plus how many status changes happened

Each interval between two samples is credited to the status of the earlier sample. An interval
longer than 3× the median sampling interval (suspend, shutdown, cron not running) counts as an
untracked gap instead.

## Cron

Sample every 5 minutes (`crontab -e`):

```cron
*/5 * * * * /path/to/battery-lab/.venv/bin/battery-lab collect >/dev/null 2>>"$HOME/.battery-lab.err"
```

**Existing cron lines keep working.** `collect.py` at the repository root is a thin shim over the
package: it needs no install, and it maps the old `--json` and `--show` flags to the new commands.
A bare `collect.py` still means `collect`.

```cron
*/5 * * * * /usr/bin/python3 /path/to/battery-lab/collect.py >/dev/null 2>>"$HOME/.battery-lab.err"
```

Paths come from the package's own location, so the working directory doesn't matter.

---

Next: [Data format](data-format.md)

[Documentation index](README.md) · [Project README](../README.md)
