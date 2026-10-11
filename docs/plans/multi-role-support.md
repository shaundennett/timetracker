# Plan: Multi-role support

Written in the structure of the `python-feature-planner` agent. Date: 2026-10-09.
Suggested branch: `feature-05`.

> Note on process: my standing instructions ask me to keep an `improvements.md`,
> but for this task I may only write inside `docs/plans/`. The future-enhancement
> ideas that would normally go there are captured under **Out of scope** below
> so nothing is lost.

## Summary

The user wants to run the app under several distinct **roles** (e.g. "Supply
teaching", "Private tutoring", "Exam marking"), each with its own completely
separate data: clients, business profile, visit records and settings. Switching
role should swap the whole dataset; invoices and tax summaries for one role must
never pull in another role's visits. The active role is remembered between runs.

The core realisation is that `Storage` is already a single-dataset object keyed
on one directory. So a role is simply **its own data directory**, and
multi-role is a thin coordination layer *above* `Storage` that points a fresh
`Storage` at the active role's folder. `invoice.py` and `tax_report.py` need no
changes at all — they already operate on whichever `Storage` they are given.

## Assumptions

- A "role" owns the full set of files `Storage` manages today: `clients.json`,
  `business.json`, `settings.json` and the monthly `time_YYYY-MM.json` files.
  Nothing is shared between roles (no shared clients or business profile).
  **Why:** the request says "its own separate data (clients, business profile,
  time records, settings)" — complete isolation, not partial.
- `--data-dir` continues to mean the **data root**. Roles become subdirectories
  of it. The default root is unchanged (`./data`, or beside the exe / under
  `~/TimeTracker/data` when frozen).
- Existing single-dataset installs must keep working: on first launch after the
  upgrade, the existing files are adopted as a default role with no data loss.
- A single user runs the app; there is no concurrent access to the data root,
  so file-level races between roles are out of scope.
- GBP, Python 3.9+, stdlib-only (plus `fpdf2`) still hold. No new dependency.

## MVP scope

The smallest system that delivers real value:

1. **Role = directory.** Each role's data lives in its own subdirectory of the
   data root. A role has a stable id (used as the folder name) and a
   human-readable display name.
2. **A manifest at the data root** (`roles.json`) listing the roles and which is
   active, managed by a new non-UI `RoleManager`.
3. **Automatic migration:** on first launch, if legacy files sit directly in the
   data root and there is no `roles.json`, adopt them as a "Default" role.
4. **Always an active role:** a fresh install with no data creates one default
   role so the app always has somewhere to write.
5. **Switch the active role** from the UI; the choice persists between runs.
6. **Create a new (empty) role** from the UI.
7. The active role name is visible (window title and a toolbar label).

That is a usable multi-role system: isolated data, create, switch, remembered.

## Out of scope

Deliberately left out of the MVP, with reasons. (These are the
"future improvements" that would normally live in `improvements.md`.)

- **Rename a role.** Pleasant but not essential; display name only, no data
  move, so it can be added later cheaply. Left out to keep the first cut small.
- **Delete a role.** Destructive and needs careful guards (can't delete the last
  or the active role without reassigning; confirmation; what happens to the
  folder). Deferred so data loss risk is not introduced early.
- **Copy/duplicate a role or copy clients between roles.** Useful for someone
  whose tutoring and marking share clients, but it is a convenience on top of
  the core feature.
- **Per-role colour/badge, or showing the role on the invoice/PDF.** Cosmetic.
- **Merging roles or cross-role reporting (combined tax year).** HMRC self-
  assessment may actually want totals across roles for one sole trader — worth
  revisiting, but a separate feature with its own design.
- **Export/backup a single role as a zip.** Nice operational feature; later.
- **Warning on unsaved form edits before switching role.** Noted as a small
  follow-up (see Risks); the MVP discards the in-progress form on switch.

## Steps

### 1. Add a `RoleManager` and `Role` model (new `timetracker/roles.py`)

**Files:** create `timetracker/roles.py`; create `tests/test_roles.py`.

- `@dataclass Role` with `id: str`, `name: str`. The id doubles as the
  subdirectory name and is generated with the existing `models._new_id()` so it
  is always filesystem-safe regardless of the display name.
  **Why an id separate from the name:** display names can contain spaces or
  slashes and may change later; a stable opaque folder id decouples rename from
  the folder and avoids path-injection via the name.
- `class RoleManager` with:
  - `__init__(self, data_root: str | os.PathLike = "data")` — stores the root,
    `self.manifest_file = data_root / "roles.json"`, ensures the root exists,
    and calls a private `_ensure_initialised()` (migration/bootstrap, step 3).
  - `list_roles(self) -> list[Role]` — read the manifest, sorted by name.
  - `active_role(self) -> Role` — the manifest's active role (guaranteed to
    exist after init).
  - `set_active(self, role_id: str) -> None` — validate the id exists, update the
    manifest, atomic write.
  - `create_role(self, name: str) -> Role` — validate name (trimmed, non-empty,
    not a case-insensitive duplicate), mint an id, create its directory, append
    to the manifest, atomic write; return the `Role`. Does **not** switch to it
    (caller decides).
  - `role_dir(self, role_id: str) -> Path` — `data_root / role_id`.
  - `storage_for(self, role_id: str) -> Storage` — `Storage(self.role_dir(id))`.
  - `active_storage(self) -> Storage` — convenience for `storage_for(active)`.
- Manifest shape:
  ```json
  {
    "active": "ab12cd34ef56",
    "roles": [
      {"id": "ab12cd34ef56", "name": "Supply teaching"},
      {"id": "7f90ab12cd34", "name": "Private tutoring"}
    ]
  }
  ```
- Reuse the atomic-write / tolerant-read pattern rather than reinventing it: see
  step 2.

**Why a new module rather than extending `Storage`:** `CLAUDE.md` says `Storage`
is a single, swappable dataset backend. Roles are a layer that *chooses which
dataset*, so they belong above `Storage`, not inside it. A future SQLite
`Storage` would still be instantiated per role directory (or per schema) without
changing `RoleManager`. This keeps `Storage`'s method signatures untouched.

**Tests (`tests/test_roles.py`):**
- fresh root with nothing in it bootstraps exactly one default role and makes it
  active.
- `create_role` makes a new subdirectory, appends to the manifest, and rejects
  blank / duplicate (case-insensitive) names with `ValueError`.
- `set_active` persists and round-trips; unknown id raises.
- `storage_for` returns a `Storage` rooted in the role's subdirectory, and two
  roles' `Storage` objects do not see each other's clients/records (isolation).
- corrupt `roles.json` recovers rather than crashing (step 6 behaviour).

### 2. Extract shared atomic JSON helpers (small change to `timetracker/storage.py`)

**Files:** edit `timetracker/storage.py`.

- Promote the existing private `_read_json` / `_write_json` bodies to
  module-level functions `read_json(path, default)` and
  `write_json(path, payload)` in `storage.py`, and have the existing
  `Storage._read_json` / `Storage._write_json` staticmethods delegate to them.
- `RoleManager` imports and uses these for the manifest.

**Why:** the manifest must be written with the same temp-file-plus-`os.replace`
atomicity the project mandates for all persistence. Reusing one implementation
avoids a second, slightly-different copy drifting out of sync. This *extends*
`storage.py` (adds module functions) without changing any existing method
signature, which satisfies the "extend rather than change" rule.

**Alternative rejected:** duplicating ~12 lines of atomic-write code inside
`roles.py`. Simpler diff, but two copies of safety-critical I/O is exactly the
kind of thing that rots.

**Tests:** existing `tests/test_storage.py` continues to pass unchanged
(behaviour identical). Optionally add one direct test of `write_json` atomicity
(temp file cleaned up, content correct).

### 3. Migration and bootstrap (inside `RoleManager._ensure_initialised`)

**Files:** `timetracker/roles.py` (logic); `tests/test_roles.py` (coverage).

Logic, run once per `RoleManager` construction:

1. If `roles.json` exists and is valid, do nothing.
2. Else, look for **legacy data** directly in the root: any of `clients.json`,
   `business.json`, `settings.json`, or `time_*.json`.
   - If found: create a default role (name `"Default"`), create its directory,
     and **copy** each legacy file into it, then write the manifest with that
     role active.
   - If none found (fresh install): create a single `"Default"` role directory
     and an empty-but-valid dataset, write the manifest.

**Why copy (not move) the legacy files:** copying leaves the originals in the
root untouched as an automatic pre-upgrade backup. Once `roles.json` exists, the
root-level files are ignored forever, so they cause no confusion; a cautious
user can delete them later. Moving would be tidier but risks data loss if
interrupted mid-migration.

**Why the manifest is written last:** it is the completion marker. If migration
is interrupted before the manifest is written, the next launch simply sees "no
manifest + legacy data present" and retries from scratch (copy is idempotent —
overwrite the half-copied role dir). So migration is safe to re-run.

**Tests:**
- a root pre-populated with fake `clients.json` + a `time_2026-07.json` becomes a
  "Default" role whose `Storage` lists those clients/records; originals still
  present in the root.
- re-running `RoleManager(root)` after migration does not duplicate or move
  anything.
- fresh empty root yields one default role with an empty client list.

(Use **fake** clients/records in fixtures — never anything from `data/`.)

### 4. Wire `RoleManager` into startup (`timetracker/__main__.py`)

**Files:** edit `timetracker/__main__.py`.

- Build a `RoleManager(args.data_dir or default_data_dir())` and pass it to
  `App` instead of a bare `Storage`.
- Keep `default_data_dir()` as-is; it now returns the data *root*.

**Why:** the data root is exactly today's data dir; roles are subdirectories, so
the CLI contract barely changes. Document in the module docstring that the data
dir is now a root containing one folder per role plus `roles.json`.

### 5. Teach `App` to hold a `RoleManager` and switch roles (`timetracker/ui/app.py`)

**Files:** edit `timetracker/ui/app.py`.

- `App.__init__(self, role_manager: RoleManager | None = None)`:
  - store `self.roles = role_manager or RoleManager()`.
  - `self.storage = self.roles.active_storage()`.
  - set the window title to `f"Time Tracker — {active.name}"`.
  - build the record tab as today, but passing `self.storage`.
- Add a **Role** cascade to the menu bar in `_build_menu`:
  - a dynamic submenu of radio items, one per role, checking the active one and
    calling `self.switch_role(role_id)`.
  - `"New role…"` → opens the new role dialog (step 6).
  - Rebuild this submenu whenever roles change (extract a
    `_rebuild_role_menu()` helper called from `__init__`, after creating a role,
    and after switching).
- `switch_role(self, role_id)`:
  - `self.roles.set_active(role_id)`.
  - `self.storage = self.roles.active_storage()`.
  - **rebuild the record tab**: destroy `self.record_tab`, construct a new one
    with the new `self.storage`, re-pack it, re-wire the dialog callbacks.
  - update the window title and the role menu checkmark.
- Open dialogs (`ClientsDialog`, `BusinessDialog`, `InvoiceDialog`,
  `TaxYearDialog`) keep using `self.storage`, so they automatically act on the
  active role.

**Why rebuild the record tab rather than re-point it:** `RecordTab` reads
`settings.period_kind` and builds its event index in `__init__`; a clean rebuild
guarantees period toggle, event dropdown, totals and form all reflect the new
role with no stale state. A `set_storage()` method that re-refreshes every widget
is more code and more bug surface for a once-in-a-while action.

**Why menu + title (not a toolbar combobox):** the record-tab toolbar is already
busy, and the app's other data-management actions are menu-driven, so a `Role`
menu matches the existing UX with minimal layout churn. A small read-only
toolbar label showing the active role can be added for at-a-glance confidence
(optional within MVP).

### 6. New-role dialog (new `timetracker/ui/role_dialog.py`)

**Files:** create `timetracker/ui/role_dialog.py`.

- A tiny `tk.Toplevel` (modelled on `business_dialog.py`): one "Name" entry,
  Save / Cancel.
- On save: call `self.roles.create_role(name)` (via a callback passed in),
  show the `ValueError` message from validation if the name is blank/duplicate,
  then ask whether to switch to the new role now (or just switch automatically —
  see Open questions), and call back into `App` to refresh the role menu.

**Why a dialog, not an inline prompt:** consistent with every other
create/edit flow in the app; leaves room to add fields later (e.g. seed the
business profile) without redesigning.

**Tests:** none for the dialog itself (UI, no headless test). The logic it calls
(`create_role`) is covered in `tests/test_roles.py`.

### 7. Docs and version bump

**Files:** `README.md` (user-facing: what a role is, how to switch/create, where
data lives, migration note), `timetracker/__init__.py` (`__version__` bump,
e.g. `0.4.0`), and this plan committed under `docs/plans/`.

**Why a minor version bump:** new user-visible feature plus an on-disk layout
change (data moves under per-role folders), so it deserves its own version. The
version lives only in `__init__.py` per the project rule.

Suggested commit sequence (one logical change each): (1) atomic JSON helpers,
(2) `RoleManager` + migration + tests, (3) `App`/`__main__` wiring + role dialog,
(4) README + version bump.

## Risks and edge cases

- **Data loss during migration.** Mitigated by copy-not-move (originals remain),
  manifest-written-last (idempotent retry), and atomic writes. Recommend the
  release notes tell users to back up `data/` before first run anyway.
- **Corrupt or partial `roles.json`.** Follow the `Settings` precedent: on
  unreadable/invalid manifest, do not crash. Recovery order: if role
  subdirectories already exist, rebuild the manifest from them (pick the first,
  or a default, as active); else fall back to bootstrap/migration. Cover with a
  test that writes `"not json"` and asserts the app still has one usable role.
- **Role name validation.** Trim; reject empty; reject case-insensitive
  duplicates. Names never touch the filesystem (the id does), so no path-safety
  issue from names. Unicode names are fine in JSON (`ensure_ascii=False` already
  set).
- **Switching role with unsaved form edits.** MVP rebuilds the tab and silently
  discards the in-progress visit. Acceptable for a deliberate action; a
  follow-up could prompt. Call this out in release notes.
- **Old JSON record format.** Unchanged — the same files simply live one folder
  deeper. The tolerant `from_dict` loaders (unpadded times, `vat_reference`
  back-compat, missing fields) keep working. No record migration needed.
- **Invoices and tax reports.** No change to `invoice.py` / `tax_report.py`.
  Because they receive the active role's `Storage`, isolation is automatic and
  there is no way for one role's visits to leak into another's invoice or tax
  summary. (This is the main reason the role=directory design is low-risk.)
- **`--data-dir` meaning changed** from "the dataset" to "the data root".
  Existing scripts pointing at an old dataset directory will trigger migration
  inside that directory on first run (adopting it as Default), which is the
  desired behaviour. Document it.
- **`available_months()` / `month_keys`.** Glob stays scoped to a single role
  directory, so no cross-role bleed. No change needed.
- **Frozen (exe) build.** `default_data_dir()` still returns a writable root;
  roles are created beneath it. `run_app.py` imports are unaffected (it imports
  the package, which now also exposes `roles.py`). Confirm the new module is
  picked up by PyInstaller (it is part of the package, so it will be).

## Verification

Automated:
- `pytest` — all existing tests must still pass (especially
  `tests/test_storage.py`, which exercises the refactored helpers, and
  `tests/test_invoice.py` / `tests/test_tax_report.py`, which prove isolation
  logic is untouched).
- new `tests/test_roles.py` — bootstrap, migration (copy + idempotent),
  create/validate, set-active round-trip, corrupt-manifest recovery, and
  cross-role isolation via two `storage_for` instances.

Manual (`python -m timetracker --data-dir <temp dir>`):
1. Point at an empty temp dir: app opens with a "Default" role; title shows it.
2. Point at a temp dir pre-seeded with **fake** `clients.json` + a
   `time_YYYY-MM.json`: app migrates them into a Default role; the existing
   clients and visits appear; originals still sit in the root.
3. Create a second role from the Role menu: it is empty (no clients, no visits,
   fresh business profile and settings).
4. Switch between roles: the client dropdown, recorded-visits list, business
   details dialog, invoice line items and tax-year summary each reflect only the
   active role.
5. Add a visit and an invoice under role A, switch to role B, confirm B's
   invoice and tax summary contain none of A's data.
6. Restart the app: the last active role is restored.

## Open questions

1. **Default role name.** Is `"Default"` acceptable for the migrated/first role,
   or should the app prompt for a name on first launch (e.g. "Supply teaching")?
2. **After creating a role, switch to it automatically, or stay put?** I lean
   towards switching automatically (the user just made it to use it), but will
   follow your preference.
3. **Should any data be shared across roles?** The plan assumes full isolation
   (including the business profile). If the same sole trader uses one business
   profile for all roles, we could share `business.json` at the root instead —
   this changes the model, so confirm before building.
4. **Combined tax-year reporting across roles.** For one sole trader, HMRC self-
   assessment may want totals across all roles. Out of scope for the MVP — do
   you want it on the roadmap?
5. **Rename / delete roles** — wanted soon after the MVP, or genuinely later?
   (Delete needs the guards described above.)
