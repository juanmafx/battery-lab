-- Optional normalized SQLite schema for battery-lab logs. The CLI stores CSV and does not require this file.
-- Requires SQLite 3.38 or newer. Apply with: sqlite3 battery.db < db/schema.sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY,
    machine_key TEXT NOT NULL UNIQUE CHECK (length(machine_key) BETWEEN 1 AND 255)
) STRICT;

CREATE TABLE IF NOT EXISTS batteries (
    id INTEGER PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines (id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 64),
    UNIQUE (machine_id, name)
) STRICT;

CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY,
    battery_id INTEGER NOT NULL REFERENCES batteries (id) ON DELETE CASCADE,
    recorded_at TEXT NOT NULL CHECK (julianday(recorded_at) IS NOT NULL),
    status TEXT,
    capacity INTEGER CHECK (capacity BETWEEN 0 AND 100),
    capacity_level TEXT,
    charge_now INTEGER CHECK (charge_now >= 0),
    charge_full INTEGER CHECK (charge_full >= 0),
    charge_full_design INTEGER CHECK (charge_full_design >= 0),
    energy_now INTEGER CHECK (energy_now >= 0),
    energy_full INTEGER CHECK (energy_full >= 0),
    energy_full_design INTEGER CHECK (energy_full_design >= 0),
    voltage_now INTEGER CHECK (voltage_now >= 0),
    voltage_min_design INTEGER CHECK (voltage_min_design >= 0),
    current_now INTEGER,
    power_now INTEGER,
    cycle_count INTEGER CHECK (cycle_count > 0),
    technology TEXT,
    model_name TEXT,
    manufacturer TEXT,
    serial_number TEXT,
    temp_c REAL CHECK (temp_c > 0 AND temp_c <= 150),
    extra TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(extra) AND json_type(extra) = 'object'),
    UNIQUE (battery_id, recorded_at)
) STRICT;

CREATE INDEX IF NOT EXISTS idx_samples_recorded_at ON samples (recorded_at);

CREATE VIEW IF NOT EXISTS sample_records AS
SELECT
    machines.machine_key AS machine_id,
    samples.recorded_at AS timestamp,
    batteries.name AS battery,
    samples.status,
    samples.capacity,
    samples.capacity_level,
    samples.charge_now,
    samples.charge_full,
    samples.charge_full_design,
    samples.energy_now,
    samples.energy_full,
    samples.energy_full_design,
    samples.voltage_now,
    samples.voltage_min_design,
    samples.current_now,
    samples.power_now,
    samples.cycle_count,
    samples.technology,
    samples.model_name,
    samples.manufacturer,
    samples.serial_number,
    CASE
        WHEN samples.charge_full > 0 AND samples.charge_full_design > 0
            THEN round(100.0 * samples.charge_full / samples.charge_full_design, 2)
        WHEN samples.energy_full > 0 AND samples.energy_full_design > 0
            THEN round(100.0 * samples.energy_full / samples.energy_full_design, 2)
    END AS health_pct,
    samples.temp_c,
    samples.extra
FROM samples
JOIN batteries ON batteries.id = samples.battery_id
JOIN machines ON machines.id = batteries.machine_id;
