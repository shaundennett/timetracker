"""Record tab: the day-to-day workflow.

Pick a date, choose one of your regular client events, tweak the pre-filled
billing fields if the actual visit differed, and save it as a VisitRecord for
that date. The lower half lists everything already recorded in the selected
month with per-day and month totals — the numbers that feed an invoice.

    ┌ Date [19/07/2026] [Today] [◀] [▶]   Event [ combo ] [Load] ┐
    │ Description / School / Times / Hours / Rate / Notes  form   │
    │ [New] [Save] [Delete]                    Amount: 90.00      │
    ├────────────────────────────────────────────────────────────┤
    │ Treeview of this month's records                            │
    │ Day total: 90.00        Month total: 1,240.00              │
    └────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from ..models import (
    DATE_FORMAT,
    WEEKDAYS,
    Client,
    VisitRecord,
    compute_hours,
    format_display_date,
    normalize_time,
)
from .date_picker import DatePicker
from .time_picker import TimePicker
from ..storage import Storage
from .style import ACCENT, BORDER, INK, SURFACE


class RecordTab(ttk.Frame):
    def __init__(self, parent, storage: Storage, on_manage_events=None,
                 on_business=None, on_invoice=None, on_tax_year=None):
        super().__init__(parent, padding=14)
        self.storage = storage
        # Callbacks that open the various dialogs; wired up by the App.
        self.on_manage_events = on_manage_events or (lambda: None)
        self.on_business = on_business or (lambda: None)
        self.on_invoice = on_invoice or (lambda: None)
        self.on_tax_year = on_tax_year or (lambda: None)
        self._current_record_id: str | None = None
        # Maps the label shown in the event combobox back to a Client.
        self._event_index: dict[str, Client] = {}

        self._build_toolbar()
        self._build_top()
        self._build_form()
        self._build_records()
        self.refresh_clients()
        self.reload_records()

    def current_month(self) -> str | None:
        """The 'YYYY-MM' currently in view — used to seed the invoice dialog."""
        return self._month_key()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Label(bar, text="Daily time entries",
                  style="Heading.TLabel").pack(side="left")
        ttk.Button(bar, text="Create invoice…", style="Accent.TButton",
                   command=lambda: self.on_invoice()).pack(side="right")
        ttk.Button(bar, text="Tax year summary…",
                   command=lambda: self.on_tax_year()).pack(
            side="right", padx=(0, 8))
        ttk.Button(bar, text="Business details…",
                   command=lambda: self.on_business()).pack(
            side="right", padx=(0, 8))
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(0, 10))

    def _build_top(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x")

        ttk.Label(top, text="Date").grid(row=0, column=0, sticky="w", padx=(0, 4))
        # Picking a date reloads the records list and event ordering.
        self.date_picker = DatePicker(top, on_change=self._on_date_change)
        self.date_picker.grid(row=0, column=1, sticky="w")

        ttk.Button(top, text="Today", command=self._go_today).grid(
            row=0, column=2, padx=4)
        ttk.Button(top, text="◀", width=3,
                   command=lambda: self._shift_day(-1)).grid(row=0, column=3)
        ttk.Button(top, text="▶", width=3,
                   command=lambda: self._shift_day(1)).grid(row=0, column=4,
                                                            padx=(0, 16))

        ttk.Label(top, text="Event").grid(row=0, column=5, sticky="w",
                                          padx=(0, 4))
        self.event_var = tk.StringVar()
        self.event_combo = ttk.Combobox(top, textvariable=self.event_var,
                                        state="readonly", width=42)
        self.event_combo.grid(row=0, column=6, sticky="w")
        # Choosing an event immediately pre-fills the form for that date.
        self.event_combo.bind("<<ComboboxSelected>>",
                              lambda _e: self._load_event())

        ttk.Button(top, text="Manage events…",
                   command=lambda: self.on_manage_events()).grid(
            row=0, column=7, padx=(12, 0))

    def _build_form(self) -> None:
        form = ttk.LabelFrame(self, text="Visit details", padding=10)
        form.pack(fill="x", pady=(4, 10))
        # A trailing spacer column soaks up extra width so the fields stay
        # compact and left-aligned instead of stretching across the window.
        form.columnconfigure(4, weight=1)

        self.vars = {
            "description": tk.StringVar(),
            "school": tk.StringVar(),
            "start_time": tk.StringVar(value="09:00"),
            "end_time": tk.StringVar(value="10:00"),
            "hours": tk.StringVar(value="1.0"),
            "rate": tk.StringVar(value="0.00"),
            "mileage": tk.StringVar(value="0"),
        }
        # Live amount preview recomputes as hours/rate change.
        for key in ("hours", "rate"):
            self.vars[key].trace_add("write", lambda *_: self._update_amount())
        # Changing a time recalculates Hours.
        for key in ("start_time", "end_time"):
            self.vars[key].trace_add("write", lambda *_: self._auto_hours())

        # Two fields per row keeps the section short.
        self._add_entry(form, "Description", "description", 0, 0, width=22)
        self._add_entry(form, "School", "school", 0, 2, width=24)
        self._add_time(form, "Start (24h)", "start_time", 1, 0)
        self._add_time(form, "End (24h)", "end_time", 1, 2)
        self._add_entry(form, "Hours", "hours", 2, 0, width=12)
        self._add_entry(form, "Rate (/hr)", "rate", 2, 2, width=12)
        self._add_entry(form, "Mileage", "mileage", 3, 0, width=12)

        # Compact multi-line notes field.
        ttk.Label(form, text="Notes").grid(row=4, column=0, sticky="nw",
                                           padx=(0, 8), pady=3)
        self.notes_text = tk.Text(
            form, height=2, width=52, wrap="word", relief="solid",
            borderwidth=1, highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, background=SURFACE, foreground=INK,
            insertbackground=INK, padx=6, pady=4, font=("Segoe UI", 10))
        self.notes_text.grid(row=4, column=1, columnspan=3, sticky="w",
                             padx=6, pady=3)

        # Actions and the live amount on one row.
        btns = ttk.Frame(form)
        btns.grid(row=5, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="New", command=self.clear_form).pack(
            side="left", padx=(0, 5))
        ttk.Button(btns, text="Save visit", style="Accent.TButton",
                   command=self._save).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", style="Danger.TButton",
                   command=self._delete).pack(side="left", padx=5)
        ttk.Label(btns, text="Amount:", style="Muted.TLabel").pack(
            side="left", padx=(20, 4))
        self.amount_var = tk.StringVar(value="0.00")
        ttk.Label(btns, textvariable=self.amount_var,
                  style="Total.TLabel").pack(side="left")

    def _add_entry(self, parent, label, key, row, col, colspan=1,
                   width=None) -> None:
        pad_left = 16 if col else 0
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w",
                                           padx=(pad_left, 8), pady=3)
        entry = ttk.Entry(parent, textvariable=self.vars[key],
                          **({"width": width} if width else {}))
        entry.grid(row=row, column=col + 1, columnspan=colspan,
                   sticky="w" if width else "ew", padx=6, pady=3)

    def _add_time(self, parent, label, key, row, col) -> None:
        pad_left = 16 if col else 0
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w",
                                           padx=(pad_left, 8), pady=3)
        TimePicker(parent, self.vars[key]).grid(
            row=row, column=col + 1, sticky="w", padx=6, pady=3)

    def _build_records(self) -> None:
        wrap = ttk.LabelFrame(self, text="Recorded visits (this month)",
                              padding=8)
        wrap.pack(fill="both", expand=True)

        columns = ("date", "description", "school", "time", "hours",
                   "rate", "miles", "amount")
        self.tree = ttk.Treeview(wrap, columns=columns, show="headings",
                                 selectmode="browse", height=10)
        headings = {
            "date": "Date", "description": "Description", "school": "School",
            "time": "Time", "hours": "Hours", "rate": "Rate",
            "miles": "Miles", "amount": "Amount",
        }
        widths = {"date": 90, "description": 190, "school": 120, "time": 100,
                  "hours": 60, "rate": 70, "miles": 60, "amount": 90}
        numeric = {"hours", "rate", "miles", "amount"}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col],
                             anchor="e" if col in numeric else "w")
        self.tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(wrap, orient="vertical",
                               command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_record_select)

        totals = ttk.Frame(self)
        totals.pack(fill="x", pady=(6, 0))
        self.day_total_var = tk.StringVar(value="0.00")
        self.month_total_var = tk.StringVar(value="0.00")
        self.month_miles_var = tk.StringVar(value="0")
        ttk.Label(totals, text="Day total:").pack(side="left")
        ttk.Label(totals, textvariable=self.day_total_var,
                  font=("", 10, "bold")).pack(side="left", padx=(4, 20))
        ttk.Label(totals, text="Month total:").pack(side="left")
        ttk.Label(totals, textvariable=self.month_total_var,
                  font=("", 10, "bold")).pack(side="left", padx=(4, 20))
        ttk.Label(totals, text="Month miles:").pack(side="left")
        ttk.Label(totals, textvariable=self.month_miles_var,
                  font=("", 10, "bold")).pack(side="left", padx=(4, 0))

    # ------------------------------------------------------------------ #
    # Date helpers
    # ------------------------------------------------------------------ #
    def _selected_date(self) -> date:
        return self.date_picker.get_date()

    def _go_today(self) -> None:
        self.date_picker.set_date(date.today())

    def _shift_day(self, delta: int) -> None:
        self.date_picker.set_date(self._selected_date()
                                  + timedelta(days=delta))

    def _on_date_change(self) -> None:
        self.refresh_clients()
        self.reload_records()

    # ------------------------------------------------------------------ #
    # Events (client picker)
    # ------------------------------------------------------------------ #
    def refresh_clients(self) -> None:
        """Rebuild the event dropdown; events matching the selected date's
        weekday are listed first so the common case is one click away."""
        clients = self.storage.list_clients()
        target_day = WEEKDAYS[self._selected_date().weekday()]

        def sort_key(c: Client):
            return (c.regular_day != target_day, c.description.lower())

        clients.sort(key=sort_key)
        self._event_index = {}
        labels = []
        for c in clients:
            school = f" — {c.school}" if c.school else ""
            label = f"{c.description}{school} ({c.regular_day} {c.start_time})"
            self._event_index[label] = c
            labels.append(label)
        self.event_combo["values"] = labels
        # Drop a stale selection that no longer exists.
        if self.event_var.get() not in self._event_index:
            self.event_var.set("")

    def _load_event(self) -> None:
        label = self.event_var.get()
        client = self._event_index.get(label)
        if client is None:
            return  # Nothing selected (or a stale selection) — ignore.
        record = VisitRecord.from_client(
            client, self._selected_date().strftime(DATE_FORMAT))
        self._current_record_id = None  # Loading an event starts a new visit.
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self._fill_form(record)

    # ------------------------------------------------------------------ #
    # Form
    # ------------------------------------------------------------------ #
    def _fill_form(self, record: VisitRecord) -> None:
        self.vars["description"].set(record.description)
        self.vars["school"].set(record.school)
        self.vars["start_time"].set(record.start_time)
        self.vars["end_time"].set(record.end_time)
        self.vars["hours"].set(f"{record.hours:g}")
        self.vars["rate"].set(f"{record.rate:.2f}")
        self.vars["mileage"].set(f"{record.mileage:g}")
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", record.notes)
        self._update_amount()

    def clear_form(self) -> None:
        self._current_record_id = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.vars["description"].set("")
        self.vars["school"].set("")
        self.vars["start_time"].set("09:00")
        self.vars["end_time"].set("10:00")
        self.vars["hours"].set("1.0")
        self.vars["rate"].set("0.00")
        self.vars["mileage"].set("0")
        self.notes_text.delete("1.0", "end")
        self._update_amount()

    def _auto_hours(self) -> None:
        """Keep Hours in step with the times; it can still be overtyped."""
        try:
            hours = compute_hours(self.vars["start_time"].get(),
                                  self.vars["end_time"].get())
        except ValueError:
            return
        if hours > 0:
            self.vars["hours"].set(f"{hours:g}")

    def _update_amount(self) -> None:
        try:
            amount = float(self.vars["hours"].get()) * float(
                self.vars["rate"].get())
        except ValueError:
            self.amount_var.set("—")
            return
        self.amount_var.set(f"{amount:.2f}")

    def _validate(self) -> VisitRecord | None:
        d = self._selected_date()
        description = self.vars["description"].get().strip()
        if not description:
            messagebox.showerror("Missing data", "Description is required.")
            return None
        try:
            start = normalize_time(self.vars["start_time"].get())
            end = normalize_time(self.vars["end_time"].get())
        except ValueError:
            messagebox.showerror("Invalid time",
                                 "Times must be 24-hour HH:MM.")
            return None
        if compute_hours(start, end) <= 0:
            messagebox.showerror("Invalid time",
                                 "End time must be after start time.")
            return None
        try:
            hours = float(self.vars["hours"].get())
            rate = float(self.vars["rate"].get())
            # Mileage is optional: blank counts as 0.
            mileage = float(self.vars["mileage"].get() or 0)
        except ValueError:
            messagebox.showerror("Invalid number",
                                 "Hours, rate, and mileage must be numbers.")
            return None

        return VisitRecord(
            client_id=self._selected_client_id(),
            date=d.strftime(DATE_FORMAT),
            description=description,
            school=self.vars["school"].get().strip(),
            start_time=start,
            end_time=end,
            hours=hours,
            rate=rate,
            mileage=mileage,
            notes=self.notes_text.get("1.0", "end").strip(),
            id=self._current_record_id or VisitRecord(
                client_id="", date="").id,
        )

    def _selected_client_id(self) -> str:
        client = self._event_index.get(self.event_var.get())
        return client.id if client else ""

    def _save(self) -> None:
        record = self._validate()
        if record is None:
            return
        self.storage.save_record(record)
        self._current_record_id = record.id
        self.reload_records()
        # Reselect the saved record if it's in the currently shown month.
        if self.tree.exists(record.id):
            self.tree.selection_set(record.id)

    def _delete(self) -> None:
        if not self._current_record_id:
            messagebox.showinfo("Nothing selected",
                                "Select a recorded visit to delete.")
            return
        if not messagebox.askyesno("Confirm delete", "Delete this visit?"):
            return
        month_key = self._month_key()
        # The record's own date drives its month file, which may differ from
        # the date box if the user edited the box after selecting the row.
        record = self._find_record(self._current_record_id)
        if record is not None:
            month_key = record.month_key
        if month_key:
            self.storage.delete_record(month_key, self._current_record_id)
        self.clear_form()
        self.reload_records()

    # ------------------------------------------------------------------ #
    # Records list
    # ------------------------------------------------------------------ #
    def _month_key(self) -> str:
        return self._selected_date().strftime(DATE_FORMAT)[:7]

    def _find_record(self, record_id: str) -> VisitRecord | None:
        month_key = self._month_key()
        return next((r for r in self.storage.list_records(month_key)
                     if r.id == record_id), None)

    def reload_records(self) -> None:
        self.tree.delete(*self.tree.get_children())
        month_key = self._month_key()
        selected_date = self._selected_date().strftime(DATE_FORMAT)
        day_total = 0.0
        month_miles = 0.0
        records = self.storage.list_records(month_key)
        for r in records:
            self.tree.insert(
                "", "end", iid=r.id,
                values=(format_display_date(r.date), r.description, r.school,
                        f"{r.start_time}-{r.end_time}", f"{r.hours:g}",
                        f"{r.rate:.2f}", f"{r.mileage:g}", f"{r.amount:.2f}"),
            )
            if r.date == selected_date:
                day_total += r.amount
            month_miles += r.mileage
        self.day_total_var.set(f"{day_total:.2f}")
        self.month_total_var.set(f"{self.storage.month_total(month_key):.2f}")
        self.month_miles_var.set(f"{round(month_miles, 2):g}")

    def _on_record_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        record = self._find_record(selection[0])
        if record is None:
            return
        self._current_record_id = record.id
        # Sync the date box to the record so edits save to the right month.
        self.date_picker.set_date(date.fromisoformat(record.date),
                                  notify=False)
        self._fill_form(record)
