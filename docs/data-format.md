# Data format

This page covers what each CSV row contains, how machines are identified, and header migration.

## What gets recorded

battery-lab reads `/sys/class/power_supply/BAT*/uevent` and parses every `KEY=value` line, so it
works on hardware other than the test bench. The tests cover a Dell, an HP that reports
`energy_*`, a dual-battery ThinkPad, a desktop with no battery, and a malformed `uevent`.

| Column | What's stored |
|---|---|
| `machine_id` | Which laptop the row came from (see [Machine identity](#machine-identity)) |
| `timestamp` | ISO 8601, with the local UTC offset |
| `battery` | Kernel name, such as `BAT0`. One row per battery, per run |
| `charge_*`, `energy_*`, `voltage_*`, `current_now`, `power_now` | Raw kernel values in µAh, µWh, µV, µA and µW. Converted only for display |
| `status`, `capacity`, `capacity_level`, `technology`, `model_name`, `manufacturer`, `serial_number` | As the kernel reports them |
| `cycle_count` | The firmware's count, or empty when it reports `0` |
| `health_pct` | `charge_full / charge_full_design × 100`, or the `energy_*` equivalent |
| `temp_c` | Hottest usable thermal zone from `/sys/class/thermal/thermal_zone*/temp`, in °C |
| `extra` | Every other `uevent` key, as JSON |

A missing or unreadable field is stored as empty (null). It never crashes the run.

**Formula protection:** text cells beginning with `=`, `+`, `-`, `@`, tab, carriage return or `'`
are written with a leading `'`, so spreadsheets do not evaluate them. battery-lab removes the mark
when it reads the file. Numeric columns are never escaped.

**File permissions:** new logs are created with mode `0600`. An existing file keeps its mode.

**When the CSV header changes:** a file from an older version that lacked a column (such as
`temp_c`) is rewritten in place with the new header, and old rows get empty values for the new
column. A header with columns this version doesn't recognize is refused, and the file is left
untouched.

### Machine identity

1. `MACHINE_ID` from `.env`, if set. Copy `.env.example` to `.env` and fill it in. Getting the
   serial needs root once: `sudo dmidecode -s system-serial-number`.
2. Otherwise `product_name` + `product_sku` from `/sys/class/dmi/id/`, which is readable without
   root (for example `Latitude-3410-09EC`).

battery-lab never reads `product_serial`, because that requires root. A test enforces it.

---

Next: [Statistical methods](methods.md)

[Documentation index](README.md) · [Project README](../README.md)
