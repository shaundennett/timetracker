# Plan: Weekly or monthly recording and invoicing

Branch: `feature-04`. Written in the structure of the `python-feature-planner` agent.

## Summary
Today everything is organised by calendar month: the entry screen lists one month of visits with day and month totals, and the invoice dialog bills one month. The user wants to choose **weekly** (a Monday to Friday working week) or **monthly**, with a toggle that switches both the visit list on the entry screen and invoice generation. The choice is remembered between runs.

## Assumptions
- "Displays of events" means the **list of recorded visits and its totals** on the entry screen. The "Manage events" dialog (the reusable event definitions) is not period-based and is unchanged.
- One preference (weekly or monthly) applies to the entry screen and to the invoice dialog's starting choice.
- Monthly stays the default, so existing users see no change until they switch.
- Weeks start on Monday (UK convention), numbered with ISO week numbers.
- The tax-year report stays monthly; HMRC summaries are by tax year, so weekly view adds nothing there.

## Key decision: what a "week" is
**Recommendation: a week is the Monday to Sunday window around a date, labelled by its Monday ("w/c Mon 06/07/2026").**

Why:
- You asked for a Monday to Friday week. That is how most visits fall, but a Saturday or Sunday visit would otherwise belong to no week and silently never be invoiced.
- Including Saturday and Sunday in the same window costs nothing when there are none, and nothing is lost when there are.
- Rejected: a strict Monday to Friday window. It is simpler to explain but hides weekend visits from both the list and the invoice, and money would go missing without any warning.
- If you would rather have a strict Monday to Friday week, only `week_of()` in the new `periods.py` changes (one line).

## Key decision: how to fetch a week without touching storage
**Recommendation: add one new method, `Storage.list_records_between(start, end)`, and leave every existing method unchanged.**

Why:
- Visits are stored in monthly files (`time_YYYY-MM.json`). A week can span two months (29 Jun to 5 Jul) or two years (28 Dec to 3 Jan), so it must read up to two files.
- The new method works out which month files overlap the range, loads them with the existing `list_records`, and keeps the records whose date falls inside. Stored dates are ISO text, so the comparison is a plain string comparison and stays correct.
- `CLAUDE.md` requires `storage.py` signatures to stay stable. Adding a method does not break that, and a future SQLite backend only has to implement one more simple query.
- Rejected: moving to weekly files. It would force a data migration and split months awkwardly.

## Key decision: where the preference is stored
**Recommendation: a small `settings.json` in the data folder, read and written through new `Storage.load_settings()` / `save_settings()`.**

Why:
- This mirrors how the business profile is stored (`business.json`), so it follows an existing pattern and keeps working if storage is swapped.
- It is saved in the data folder, so it moves with the user's data and the portable exe.
- Rejected: remembering it only for the session (the choice would reset every launch), or a registry/OS setting (not portable, not testable).

## MVP scope
1. A display-free `periods.py` that describes a month or a week and can move to the next or previous one.
2. A saved preference: weekly or monthly (default monthly).
3. A **View: Month / Week** toggle on the entry screen. The visits list, its heading, the totals and the miles figure follow it.
4. The invoice dialog starts in the saved mode and has the same toggle. In week mode you pick a week with previous and next buttons; in month mode the existing year and month boxes are used.
5. Weekly invoice numbers (for example `INV-2026W28`) and a period line on the invoice ("Week commencing 06/07/2026" or "July 2026").
6. Tests for all new logic, README and `CLAUDE.md` updates, version bump to 0.3.0.

## Out of scope
- Strict Monday to Friday weeks, unless you choose that option below.
- Changes to the tax-year report.
- Invoicing several weeks on one invoice (the monthly mode already covers a whole month).
- Other week starts, such as Sunday, or custom pay periods.
- Any change to how visits are saved: files stay monthly and no data is migrated.

## Steps

### 1. `timetracker/periods.py` (new, no UI code)
- A small frozen dataclass `Period` with `kind` (`"month"` or `"week"`), `start`, `end` (inclusive dates), and properties `label`, `title`, `month_keys` (the `YYYY-MM` files it touches).
- Functions: `period_for(kind, d) -> Period`, `shift(period, n) -> Period` (next or previous), `week_of(d)`, `month_of(d)`.
- Why: all the date arithmetic lives in one testable place, so the entry screen and the invoice dialog cannot disagree about where a week starts. It uses only `datetime` and `calendar`, so no new dependency and Python 3.9 is fine.
- Tests (`tests/test_periods.py`): a normal week; Monday and Sunday belong to the same week; a week across a month end (29 Jun to 5 Jul 2026); across a year end (28 Dec 2026 to 3 Jan 2027, where ISO week 53 or week 1 applies); leap day; shifting forward and back across month and year; labels.

### 2. Settings model and storage
- `models.py`: add a `Settings` dataclass with `period_kind: str = "month"`, plus `to_dict` and `from_dict` that ignore unknown fields (same pattern as `BusinessProfile`). An unknown or missing value falls back to `"month"`.
- `storage.py`: add `load_settings()` and `save_settings()` using the existing atomic `_write_json`.
- Tests: default when no file, round trip, corrupt file falls back, invalid value falls back.

### 3. `Storage.list_records_between(start: date, end: date)`
- Loads each overlapping month with `list_records`, filters on the ISO date string, and returns them in the usual date and start-time order.
- Tests: inside one month; across two months; across a year end; empty week; a record on the first and last day (inclusive); results are sorted.

### 4. `invoice.py`
- Add `suggest_number_for_period(period)`: monthly gives `INV-202607` (unchanged), weekly gives `INV-2026W28`, using the ISO year so the week around New Year gets the right number. Keep `suggest_number(month_key)` exactly as it is.
- Add an optional `period: str = ""` field to `Invoice`, rendered as a "Period" line in the text preview and the PDF when it is set.
- Why: a weekly invoice that shows only an invoice date does not tell the school which week it covers.
- Tests: weekly and monthly numbers (including the New Year week); the period line appears and is omitted when empty; existing invoice tests still pass unchanged.

### 5. Entry screen (`ui/record_tab.py`)
- Add the **View: ( ) Month ( ) Week** radio buttons in the top row; changing it saves the preference and reloads the list.
- Keep `self.period` in step with the date picker and the toggle. `reload_records` uses `list_records_between(period.start, period.end)`.
- The list heading, totals and miles label follow the mode: "Recorded visits (this week)" with a **Week total** / **Week miles**, or the existing month wording.
- `_find_record`, the delete path and the "reselect after save" check currently assume the month; change them to look inside the current period. Deleting still uses the record's own `month_key`, so it keeps writing to the right file.
- `current_month()` becomes `current_date()` plus the chosen mode, which is what the invoice dialog needs.
- The Today and ◀ ▶ buttons still move by one day; the week shown is simply the one containing the chosen date.
- Why: nothing about saving a visit changes, so the risk is limited to which records are shown.

### 6. Invoice dialog (`ui/invoice_dialog.py`)
- Add the same Month / Week radio at the top of the options panel, starting from the saved preference. Changing it saves the preference too.
- Month mode: the existing year and month boxes. Week mode: a label showing the week plus ◀ ▶ buttons to move week by week, starting from the week that was on screen.
- `_month_key()` and `_month_records()` become a `_period()` and `_period_records()`; the school filter, the suggested number and the preview all use them.
- Why: week-by-week buttons are quicker than a year and week-number dropdown and reuse the same `shift()` logic as the tests.

### 7. Docs and version
- README: describe the toggle and weekly invoices. `CLAUDE.md`: note that periods live in `periods.py`, the preference in `settings.json`, and that storage stays monthly.
- Bump `__version__` to `0.3.0` (one place, as `CLAUDE.md` says).

## Risks and edge cases
- **Selection bugs on the entry screen:** the list, the selected row and the date box must agree after switching modes, saving, editing and deleting. Covered by the manual checks below.
- **Weeks spanning two files:** the main reason for the new storage method; tested at month and year boundaries.
- **A record whose date is outside the shown week** (for example after editing its date): handled the same way as outside the shown month today, it simply isn't listed.
- **Totals mismatch:** `Storage.month_total` stays for the monthly view; the weekly total is summed from the same list as the rows, so it always matches what is shown.
- **Existing data:** no migration. A missing `settings.json` means monthly.
- **Invoice numbers:** weekly numbers can clash if you invoice the same week twice; as today, the number is only a suggestion you can edit.
- **Python 3.9:** use `from __future__ import annotations`, and `Optional[...]` in anything evaluated at runtime.
- **PyInstaller:** only the standard library is added, so no build changes.

## Verification
1. `pytest` passes, including the new tests for periods, settings, `list_records_between` and invoice numbering. (pytest could not be installed on this machine earlier because pip cannot reach PyPI; if that is still the case, the stand-in runner can be used.)
2. Run `python -m timetracker --data-dir <temp dir>` with fake data covering: a week inside one month, the 29 Jun to 5 Jul week, and the week around New Year.
   - Monthly mode looks exactly as before.
   - Switching to Week shows only that week's visits, with the heading and totals changing to "week".
   - Restarting the app keeps the chosen mode.
   - Saving, editing and deleting a visit in week mode update the list and totals correctly.
   - The invoice dialog opens in the saved mode; in week mode the ◀ ▶ buttons change the week, the preview shows only that week, the number is `INV-YYYYWnn`, and the period line shows.
   - The PDF for a weekly invoice has the right lines and period.
3. `git status` shows nothing under `data/`.

## Decisions (confirmed by the user)
1. **Week window:** Monday to Sunday, labelled by its Monday. A Saturday or Sunday visit belongs to the week it falls in.
2. **Invoice period line:** yes, invoices show the period ("Week commencing 06/07/2026" or "July 2026").
3. **Preference:** one saved setting shared by the entry screen and the invoice dialog.
4. **Weekly invoice number:** `INV-2026W28` style (ISO year and week).

## Open questions
None remaining. Ready to build on `feature-04`.
