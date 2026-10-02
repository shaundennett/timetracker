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
- `timetracker/periods.py` – month / Monday–Sunday week `Period` maths (no UI); used by the record tab, invoice dialog and `Storage.list_records_between`
- `timetracker/invoice.py` – invoice building, text preview, PDF via fpdf2
- `timetracker/tax_report.py` – UK tax year (6 Apr – 5 Apr) summaries
- `timetracker/ui/` – tkinter UI (`app.py` main window, `record_tab.py` daily entry, dialogs, `style.py` theme)
- `run_app.py` – PyInstaller entry point (absolute imports on purpose)

## Conventions and gotchas

- Only third-party dependency is `fpdf2`; keep everything else stdlib.
- Visit records snapshot billing fields from the client, so changing a client's rate must never rewrite past visits.
- Mileage is tracked per visit but is deliberately not shown on invoices.
- Dates are stored as ISO `YYYY-MM-DD` (sorts correctly) and shown as `DD/MM/YYYY`. Convert only at the UI/print boundary with `models.format_display_date`; use `ui/date_picker.DatePicker` for date entry.
- Times are 24-hour `HH:MM`, zero-padded (so they sort as text). Use `ui/time_picker.TimePicker` for time entry and `models.normalize_time` to validate/normalise.
- The version number lives only in `timetracker/__init__.py` (`__version__`); `pyproject.toml` reads it. Bump it there and nowhere else.
- Visits are listed and invoiced by month or by Monday–Sunday week (`Settings.period_kind`, saved in `settings.json`). Files stay monthly; use `Storage.list_records_between` for ranges that can span two files.
- Currency is GBP (£). Python 3.9+ compatible.
- Keep UI logic out of `models`, `storage`, `invoice` and `tax_report` so they stay testable without a display. Add tests in `tests/` for logic changes.
- `storage.py` is designed to be swappable; keep its method signatures stable.

## Git workflow

- Never commit directly to `main`. Work on a branch named `feature-NN` (or `fix-<topic>`); if on `main`, create a branch first.
- Ask before committing. When a logical change is finished and `pytest` passes, offer to commit it and wait for approval; never commit on your own. Propose one commit per logical change (e.g. model helper, then UI wiring, then docs) rather than one large commit at the end. Do not commit work that is broken or half-done.
- Before committing, run `git status` and `git diff --staged`. Stage files by name, not `git add -A`, so nothing unintended (especially `data/`, `.env`, credentials) is included. Never use `--no-verify` or amend/force-push commits that have already been pushed.
- Do not push, open pull requests, merge or delete branches unless asked.

### Pull requests

Only after a commit has been explicitly approved, offer to open a PR, and wait for a yes before pushing or creating it. Approval to commit is not approval to push or open a PR.

1. Check you are on a feature branch (not `main`) and the working tree is clean: `git status`.
2. Run `pytest` and confirm it passes. Say so plainly if it cannot be run.
3. Push the branch: `git push -u origin <branch>`. If there is no `origin` yet, say so and offer to create the repo first (`gh repo create timetracker --private --source . --push`).
4. Create the PR against `main` with the GitHub CLI (`"C:\Program Files\GitHub CLI\gh.exe"` if `gh` is not on PATH; the user must have run `gh auth login`):
   `gh pr create --base main --title "<title>" --body "<body>"`
5. Report the PR URL.

PR title: same style as a commit subject (imperative, ~50 characters, describes the change). For a branch with several commits, summarise the whole change rather than copying the last commit.

PR body, in this order:
- **Summary**: 1-3 bullets on what changed and why.
- **Changes**: the main files or areas touched, one line each.
- **Testing**: what was run (`pytest` result) and anything checked by hand in the app.
- **Notes**: data-format impact (stored JSON changes), follow-ups, or open questions. Omit if none.

End the PR body with the attribution line Claude Code provides. Never include real data from `data/` in a PR title, body or comment. Do not merge the PR; leave that to the user.

### Commit messages

- Subject line: imperative mood, max ~50 characters, no trailing full stop. Say what the change does, e.g. `Add DD/MM/YYYY date picker to record tab`, not `fixed stuff` or `updates`.
- Leave a blank line, then a body (wrapped at ~72 characters) for anything non-trivial. Explain **why** the change was made and any decision a reader would otherwise question (e.g. "dates stay ISO in storage so they sort correctly"). The diff already shows what changed.
- Mention user-visible behaviour changes and any data-format impact. Never include real data from `data/` (names, schools, UTR, amounts) in a message.
- Keep the attribution trailer that Claude Code adds at the end of the message.

## Privacy

`data/` contains real personal and client information (UTR, address, phone, school names). It is git-ignored. Never commit it, paste its contents into issues or commit messages, or use it as test fixtures; use fake data in tests.
