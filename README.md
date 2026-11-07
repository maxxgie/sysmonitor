# System Monitor

Professional desktop system monitor built in Python with PyQt5 and psutil.
Built phase by phase; this is **Phase 1 — Application foundation**, expanded
with live metrics and system information.

## Colour scheme

Blue and white throughout. A dark variant is available in `ui/themes.py` and
can be selected from the Settings page.

## Features (Phase 1)

- Live Dashboard: CPU %, RAM %, disk %, upload/download speed (refreshes every second)
- System Information: OS, hostname, architecture, CPU count, uptime, boot time
- Status bar: live CPU/RAM indicators and clock
- Settings: theme (Blue & White / Dark), refresh interval, graph history
- Sidebar navigation with page switching
- Logging: console + rotating file log
- Settings persistence: survives restart via SQLite

## Requirements

- Python 3.9+
- PyQt5
- psutil

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python main.py
```

## Phase 1 gate

- [x] App launches without errors
- [x] Dashboard shows live metrics (CPU, RAM, disk, network)
- [x] Pages switch from the sidebar
- [x] System Information page loads
- [x] A changed setting survives a restart (theme, refresh interval, history)
- [x] Status bar updates live
- [x] A log file is written to the app-data folder

## Project structure

```
main.py               # entry point
requirements.txt
README.md
core/
  app.py              # composition root (dependency injection)
  database.py         # SQLite wrapper, schema + migrations
  logger.py           # console + rotating file logging
  settings.py         # typed preferences store with live signals
ui/
  main_window.py      # shell: sidebar + stacked pages + status bar
  sidebar.py          # navigation rail
  dashboard.py        # live summary cards (CPU, Memory, Storage, Network)
  settings_page.py    # theme, refresh interval, history points
  system_info.py      # OS / hardware / uptime details
  themes.py           # blue & white palette + QSS
modules/              # feature modules (added in phases 2-7)
assets/               # icons, fonts, images
tests/                # tests
plugins/              # plugin system (phase 8)
```

## Data & storage

SQLite database and logs live in the platform app-data folder:

- Linux: `~/.local/share/SystemMonitor/`
- macOS: `~/Library/Application Support/SystemMonitor/`
- Windows: `%APPDATA%\SystemMonitor`

## Next phase

Phase 2 adds the CPU module (name, core count, usage %, frequency, live graph).
