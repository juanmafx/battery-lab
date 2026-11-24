# Known quirks

This page covers firmware and sensor oddities, and how battery-lab handles each one.

| Quirk | How battery-lab handles it |
|---|---|
| Dell firmware reports `cycle_count` as `0` | Stored as empty, never as zero. A literal `0` would corrupt any analysis over time, so `0` or less always means "not reported". |
| `temp_c` is not the battery's own temperature | It's the hottest thermal zone, usually the CPU package (`x86_pkg_temp`). The Dell's battery doesn't report a temperature. Read `temp_c` as chassis heat, next to `status` and `current_now`. |
| Some battery drivers do report `POWER_SUPPLY_TEMP` | It's captured automatically in the `extra` column. |
| The CPU package temperature reacts within milliseconds | Any single reading is noisy. Trust the trend across many samples. |
| Some zones can't be read, such as a Wi-Fi card that's switched off ("No data available") | Skipped. |
| Placeholder or broken sensors report 0 °C or less, or above 150 °C | Skipped. If no zone is usable, `temp_c` is empty. |
| The kernel reports temperature in millidegrees | Stored as °C. Dividing by 1000 loses no precision. |
| Drivers disagree on the sign of `CURRENT_NOW` while discharging | Read `STATUS` for the direction of current, not the sign. |
| Threshold oscillation | Changing charge thresholds while the battery sits ABOVE the new ceiling leaves Dell firmware flipping between `Charging` and `Not charging` every few seconds. The battery must drop into the configured range before the firmware applies them cleanly. Unplug and let it discharge into the window. Until then the log shows a high raw status-change count. |
| Cron doesn't run while the laptop is suspended | Those periods show up as untracked gaps in `battery-lab show`. |

---

Next: [Architecture](ARCHITECTURE.md)

[Documentation index](README.md) · [Project README](../README.md)
