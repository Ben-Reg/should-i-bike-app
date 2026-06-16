# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

Must be run from the project root (not from inside `should-i-bike/`), because `db.py` uses the relative path `should-i-bike/should-i-bike.db`:

```bash
source venv/bin/activate
cd /path/to/should-i-bike
python should-i-bike/should-i-bike.py
```

Dependencies: `pip install -r requirements.txt` (installs `noaa_sdk` and `tabulate`).

## Architecture

`Should_I_Bike` (`should-i-bike.py`) is the central controller. It owns instances of three collaborators, each of which receives a back-reference to the controller:

- **`Weather`** (`weather.py`) — fetches NOAA hourly and grid forecasts, caches them for 60 minutes. The grid forecast (`forecastGridData`) provides extra fields (wind gust, visibility) that get merged into the hourly forecast via `addGridElementToHourly`. Unit conversions (°C→°F, km/h→mph, m→yards, angle→cardinal direction) are registered in `self.conversions` and applied automatically by `getForecastValue`.

- **`DB`** (`db.py`) — wraps SQLite at `should-i-bike/should-i-bike.db`. **Important:** `build_db()` drops and recreates all tables on every startup, so rules entered during a session do not persist to the next run. Settings are re-seeded from defaults each time as well.

- **`CLI_Interface`** (`cli_interface.py`) — all user I/O; uses `tabulate` with `fancy_grid` for tables.

## Rule evaluation model

Rules are hierarchical: **Rule → Rule Groups (AND/OR) → Elements** (comparisons against a weather metric).

- A group evaluates true if all its elements pass (AND) or any element passes (OR).
- A rule evaluates true if all its groups evaluate true.
- When a rule is true, its `weight` is added to `score`.
- `score < 10` → bike; `score >= 10` → drive.

Rules are tied to either the `Departure` or `Return` trip time, so elements are evaluated against the forecast at the appropriate hour.

## Known issues / gotchas

- **DB reset on startup**: `build_db` unconditionally drops all tables, so no data survives between runs. Rules and custom settings must be re-entered each session.
- **Timezone hardcoded**: `getForecastValue` parses times with a fixed `-05:00` offset (`weather.py:224`), which will be wrong outside US Central time.
- **`updateSetting` signature mismatch**: The property setters in `should-i-bike.py` call `self.db.updateSetting(name, value, description=...)` with a `description` keyword arg, but `DB.updateSetting` only accepts `(settingName, value)` — the description is silently ignored (and would raise `TypeError` if passed positionally).
- **`rule_types` missing `weather_element` column**: `db.py:73` creates `rule_types` with only a `name` column, but `getRules` queries `rt.weather_element` — this will error when rules with groups are evaluated.
