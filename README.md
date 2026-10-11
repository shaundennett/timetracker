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
- **Role** — a completely separate dataset (v0.4.0+): clients, visits, business
  profile, and settings are isolated per role. Use multiple roles to track
  different kinds of work (e.g. "Supply teaching", "Private tutoring", "Exam
  marking") and switch between them. Each role has its own invoices and tax
  reports. On first upgrade, existing data is migrated into a "Default" role.

## Layout

```
timetracker/
  models.py        Client and VisitRecord dataclasses + time/amount helpers
  storage.py       JSON persistence (clients.json + time_YYYY-MM.json per month)
  roles.py         multi-role support: role manager and manifest (v0.4.0+)
  periods.py       month / Monday-Sunday week date arithmetic
  invoice.py       build/render invoices (text preview + PDF via fpdf2)
  tax_report.py    UK tax year summaries (payments + mileage by month)
  ui/
    app.py            main window (entry screen + Events/Invoice/Role/Help menus)
    record_tab.py     daily workflow: pick date -> pick event -> save visit
    date_picker.py    read-only DD/MM/YYYY box with calendar popup
    time_picker.py    24-hour HH and MM boxes for start/end times
    about_dialog.py   Help > About (version number)
    clients_dialog.py modal dialog wrapping the event management panel
    clients_tab.py    management panel for the reusable event definitions
    business_dialog.py edit your business/invoice details
    invoice_dialog.py  create, preview, save-as-PDF, and print invoices
    tax_year_dialog.py UK tax year summary report
    role_dialog.py     create/rename/recolour/delete roles
    style.py          app-wide ttk theme (colours, fonts, tables, buttons)
  __main__.py      entry point
data/              data root (contains one folder per role + roles.json manifest)
  Default/         first role's data (clients.json, business.json, time_*.json)
  <role-id>/       other roles' data directories
  roles.json       role manifest (which role is active, list of all roles)
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
5. Use the **View: Month / Week** toggle (top right) to list a Monday-to-Sunday
   week instead of a month. The heading and totals switch to *week commencing
   dd/mm/yyyy*, and your choice is remembered (`settings.json`).

**Mileage** is optional on each visit (0 by default) and pre-fills from the
event's default. It is *not* shown on invoices — it's tracked separately (with a
monthly total) for mileage-based tax calculations.

## Multiple roles (v0.4.0+)

If you track multiple income streams (e.g. supply teaching, private tutoring, exam marking), use **roles** to keep them completely separate. Each role has its own clients, visits, business profile, and invoices.

To create and switch roles:

1. Click **Role** in the menu bar.
2. **New role…** creates a new empty role. When you create a role, you can
   optionally copy the business profile (name, address, UTR, etc.) from an
   existing role to save re-entering it. The new role is active immediately.
3. **Role name** (the radio buttons) switch between roles. Each switch is instant
   — no data loss, and your place in the active role is remembered.
4. **Rename active role…** and **Delete active role…** manage roles. Rename is
   safe; delete removes the role and all its data (with confirmation).
5. **Change colour of active role…** (v0.5.0+) sets the role's accent colour
   (buttons, headings, totals, focus outlines) from a preset swatch row or a
   custom colour, so you can tell roles apart at a glance. You can also pick a
   colour when creating a role.

The window title shows the active role name. On first upgrade from v0.3 or
earlier, your existing data is migrated into a "Default" role with no loss.

## Invoicing

1. Enter your details once via **Events ▸ Business details…** — full name,
   business name, UTR, telephone, email, and address. These form the
   "From" block on every invoice.
2. Click **Create invoice…** (toolbar or *Invoice* menu). Under **Bill by**,
   choose **Month** (pick the year and month) or **Week** (step through weeks
   with ◀ ▶; numbers look like `INV-2026W28`), and optionally narrow to a
   single school; the line items pre-fill. The invoice shows the period it
   covers. The Month/Week choice is the same setting as the entry screen's.
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

As of v0.4.0, the data directory is a **root** containing one folder per role
plus a manifest:

- `roles.json` — the role manifest (list of roles, which is active). Created
  automatically on first run.
- Each role's folder contains:
  - `clients.json` — all client definitions for this role.
  - `settings.json` — preferences for this role (Month/Week view, etc.).
  - `time_YYYY-MM.json` — one file per month of visit records.

On first upgrade from v0.3 or earlier, existing `clients.json`, `business.json`,
`settings.json`, and `time_*.json` files in the data directory are copied into
a new "Default" role folder (originals left in place as a backup); `roles.json`
is created to complete the migration.

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
