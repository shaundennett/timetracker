# Time Tracker

A small desktop app for recording **billable client visits** and producing the
monthly totals that feed an invoice. Built for a peripatetic teacher who visits
schools on a regular schedule but needs to log what *actually* happened each day.

No database, no server — just a tkinter GUI over plain JSON files.

## Concepts

- **Client** — a reusable *regular visit* definition: short description, school,
  regular day, start/end time, default hours, hourly rate, and default mileage.
  Defined once and reused (e.g. "Maths support, Oakwood School, every Tuesday
  09:00–10:30").
- **Visit record** — an *actual visit* on a specific date. Created by picking a
  client event for a date and confirming/adjusting the pre-filled fields. Each
  record **snapshots** its billing fields, so changing a client's rate later
  never rewrites past visits.

## Layout

```
timetracker/
  models.py        Client and VisitRecord dataclasses + time/amount helpers
  storage.py       JSON persistence (clients.json + time_YYYY-MM.json per month)
  invoice.py       build/render invoices (text preview + PDF via fpdf2)
  tax_report.py    UK tax year summaries (payments + mileage by month)
  ui/
    app.py            main window (entry screen + Events/Invoice/Help menus)
    record_tab.py     daily workflow: pick date -> pick event -> save visit
    date_picker.py    read-only DD/MM/YYYY box with calendar popup
    time_picker.py    24-hour HH and MM boxes for start/end times
    about_dialog.py   Help > About (version number)
    clients_dialog.py modal dialog wrapping the event management panel
    clients_tab.py    management panel for the reusable event definitions
    business_dialog.py edit your business/invoice details
    invoice_dialog.py  create, preview, save-as-PDF, and print invoices
    tax_year_dialog.py UK tax year summary report
    style.py          app-wide ttk theme (colours, fonts, tables, buttons)
  __main__.py      entry point
data/              JSON files created at runtime (default location)
```

The only third-party dependency is **fpdf2** (a pure-Python PDF writer) for
invoice export; everything else is the standard library.

## Running

Requires Python 3.9+ with tkinter (bundled with the standard CPython installer
on Windows and macOS; on Debian/Ubuntu install `python3-tk`).

```bash
python -m timetracker                 # data stored in ./data
python -m timetracker --data-dir path # use a different data folder
```

Or install it and use the launcher:

```bash
pip install -e ".[dev]"
timetracker
```

## Daily workflow

1. Click **Manage events…** (or the *Events* menu) and define your regular
   visits once in the dialog (description, school, day, times, hours, rate).
2. Back on the entry screen, set the date (defaults to today). Click the date
   box or 📅 to open the calendar picker, or use *Today* / ◀ / ▶ to move around.
   Dates are shown as DD/MM/YYYY and can't be typed, so they are always valid.
   Events matching that weekday are listed first.
   Start and end times use 24-hour hour/minute boxes (00-23, 00-59); **Hours**
   updates automatically when a time changes and can still be overtyped. The
   end time must be after the start time.
3. Pick an event — the form is **pre-filled automatically**. Adjust anything
   that differed on the day, add notes, and **Save visit**.
4. The lower list shows every recorded visit for that month, with **day** and
   **month** totals plus **month miles**. Click a row to **edit** it, or select
   it and **Delete**.

**Mileage** is optional on each visit (0 by default) and pre-fills from the
event's default. It is *not* shown on invoices — it's tracked separately (with a
monthly total) for mileage-based tax calculations.

## Invoicing

1. Enter your details once via **Events ▸ Business details…** — full name,
   business name, UTR, telephone, email, and address. These form the
   "From" block on every invoice.
2. Click **Create invoice…** (toolbar or *Invoice* menu). Choose the **year and
   month**, and optionally narrow to a single school; the line items pre-fill.
3. Adjust the invoice number, date, and notes — the preview updates live.
4. **Save as PDF…** writes a formatted PDF anywhere you choose; **Print** sends
   it to your default printer (via the system PDF handler).

Amounts are shown in **£** (GBP). The total is simply the sum of the visits in
the period.

## Tax year summary

For UK Self Assessment and mileage claims, use **Invoice ▸ Tax year summary…**
(or the toolbar button). Choose a **tax year** — e.g. **2026/27** covers
**6 April 2026 through 5 April 2027**. The report lists **payments** and
**mileage** for each month in that period, plus grand totals. Visits on the
boundary dates (6 April at the start, 5 April at the end) are included;
visits outside the range are excluded even if they fall in the same calendar
month file.

## Data files

- `clients.json` — all client definitions.
- `time_YYYY-MM.json` — one file per month of visit records, keeping each
  billing period self-contained.

Writes are atomic (temp file + replace), so an interrupted save can't corrupt
existing data.

## Distributing (single-file .exe)

To hand the app to someone who doesn't have Python, build a single self-contained
executable with **[build.bat](build.bat)** (run [start.bat](start.bat) once first
to create the `.venv`):

```
build.bat
```

This produces one file — **`dist\TimeTracker.exe`** (~22 MB) — that bundles
Python, tkinter, and fpdf2. Copy just that file to any Windows machine and
double-click it; no installation required.

A packaged exe stores its data in a `data` folder **next to the .exe** when that
location is writable (so it stays portable — keep the exe and its `data` folder
together), otherwise under `~/TimeTracker/data`.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The tests cover the models and storage layer and run headless (no GUI), so they
work on any OS.
