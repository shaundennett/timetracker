# Time Tracker

Desktop app (tkinter + plain JSON files) for logging billable school visits and producing monthly invoices and UK tax-year summaries. See `README.md` for user-facing docs.

## Commands

- Run: `python -m timetracker [--data-dir PATH]` (data defaults to `./data`)
- Install for dev: `pip install -e ".[dev]"`
- Test: `pytest` (headless; covers models, storage, invoice, tax report)
- Build Windows exe: `build.bat` (needs `.venv` from `start.bat`); output `dist\TimeTracker.exe`

## Layout

- `timetracker/models.py` – `Client`, `VisitRecord`, `BusinessProfile` dataclasses and time/amount helpers
- `timetracker/storage.py` – JSON persistence; `clients.json`, `business.json`, `time_YYYY-MM.json`. Atomic writes (temp file + replace)
- `timetracker/invoice.py` – invoice building, text preview, PDF via fpdf2
- `timetracker/tax_report.py` – UK tax year (6 Apr – 5 Apr) summaries
- `timetracker/ui/` – tkinter UI (`app.py` main window, `record_tab.py` daily entry, dialogs, `style.py` theme)
- `run_app.py` – PyInstaller entry point (absolute imports on purpose)

## Conventions and gotchas

- Only third-party dependency is `fpdf2`; keep everything else stdlib.
- Visit records snapshot billing fields from the client, so changing a client's rate must never rewrite past visits.
- Mileage is tracked per visit but is deliberately not shown on invoices.
- Currency is GBP (£). Python 3.9+ compatible.
- Keep UI logic out of `models`, `storage`, `invoice` and `tax_report` so they stay testable without a display. Add tests in `tests/` for logic changes.
- `storage.py` is designed to be swappable; keep its method signatures stable.

## Privacy

`data/` contains real personal and client information (UTR, address, phone, school names). It is git-ignored. Never commit it, paste its contents into issues or commit messages, or use it as test fixtures; use fake data in tests.
