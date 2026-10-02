"""Clients tab: CRUD for the reusable regular-visit definitions.

Left side  = list of existing clients (a Treeview).
Right side = an edit form. Selecting a row loads it into the form; "New"
clears the form; "Save" upserts; "Delete" removes.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..models import WEEKDAYS, Client, compute_hours, parse_time
from ..storage import Storage


class ClientsTab(ttk.Frame):
    def __init__(self, parent, storage: Storage, on_change=None):
        super().__init__(parent, padding=10)
        self.storage = storage
        # Callback so other tabs (e.g. recording) can refresh their client list.
        self.on_change = on_change or (lambda: None)
        self._current_id: str | None = None

        self._build_list()
        self._build_form()
        self.refresh()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_list(self) -> None:
        left = ttk.Frame(self)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(left, text="Potential visits (regular events)",
                  font=("", 10, "bold")).pack(anchor="w")

        columns = ("description", "school", "day", "time", "rate", "mileage")
        self.tree = ttk.Treeview(left, columns=columns, show="headings",
                                 selectmode="browse", height=18)
        headings = {
            "description": "Description",
            "school": "School",
            "day": "Day",
            "time": "Time",
            "rate": "Rate",
            "mileage": "Miles",
        }
        widths = {"description": 180, "school": 130, "day": 90,
                  "time": 100, "rate": 70, "mileage": 60}
        numeric = {"rate", "mileage"}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col],
                             anchor="e" if col in numeric else "w")
        self.tree.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(left, orient="vertical",
                               command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_form(self) -> None:
        right = ttk.LabelFrame(self, text="Event details", padding=10)
        right.pack(side="right", fill="y")

        self.vars = {
            "description": tk.StringVar(),
            "school": tk.StringVar(),
            "regular_day": tk.StringVar(value="Monday"),
            "start_time": tk.StringVar(value="09:00"),
            "end_time": tk.StringVar(value="10:00"),
            "hours": tk.StringVar(value="1.0"),
            "rate": tk.StringVar(value="0.00"),
            "mileage": tk.StringVar(value="0"),
        }

        row = 0
        self._add_entry(right, "Description", "description", row); row += 1
        self._add_entry(right, "School", "school", row); row += 1

        ttk.Label(right, text="Regular day").grid(row=row, column=0,
                                                  sticky="w", pady=3)
        ttk.Combobox(right, textvariable=self.vars["regular_day"],
                     values=WEEKDAYS, state="readonly", width=22).grid(
            row=row, column=1, sticky="w", pady=3)
        row += 1

        self._add_entry(right, "Start time (HH:MM)", "start_time", row); row += 1
        self._add_entry(right, "End time (HH:MM)", "end_time", row); row += 1

        # Recompute hours from the times as a convenience.
        ttk.Button(right, text="Calc hours from times",
                   command=self._calc_hours).grid(row=row, column=1,
                                                  sticky="w", pady=(0, 3))
        row += 1

        self._add_entry(right, "Hours", "hours", row); row += 1
        self._add_entry(right, "Rate (per hour)", "rate", row); row += 1
        self._add_entry(right, "Mileage (round trip)", "mileage", row); row += 1

        btns = ttk.Frame(right)
        btns.grid(row=row, column=0, columnspan=2, pady=(12, 0), sticky="w")
        ttk.Button(btns, text="New", command=self.clear_form).pack(
            side="left", padx=(0, 5))
        ttk.Button(btns, text="Save", style="Accent.TButton",
                   command=self._save).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete", style="Danger.TButton",
                   command=self._delete).pack(side="left", padx=5)

    def _add_entry(self, parent, label, key, row) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0,
                                           sticky="w", pady=3)
        ttk.Entry(parent, textvariable=self.vars[key], width=24).grid(
            row=row, column=1, sticky="w", pady=3)

    # ------------------------------------------------------------------ #
    # Behaviour
    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for client in self.storage.list_clients():
            self.tree.insert(
                "", "end", iid=client.id,
                values=(
                    client.description,
                    client.school,
                    client.regular_day,
                    f"{client.start_time}-{client.end_time}",
                    f"{client.rate:.2f}",
                    f"{client.mileage:g}",
                ),
            )

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        client = self.storage.get_client(selection[0])
        if client is None:
            return
        self._current_id = client.id
        self.vars["description"].set(client.description)
        self.vars["school"].set(client.school)
        self.vars["regular_day"].set(client.regular_day)
        self.vars["start_time"].set(client.start_time)
        self.vars["end_time"].set(client.end_time)
        self.vars["hours"].set(f"{client.hours:g}")
        self.vars["rate"].set(f"{client.rate:.2f}")
        self.vars["mileage"].set(f"{client.mileage:g}")

    def clear_form(self) -> None:
        self._current_id = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.vars["description"].set("")
        self.vars["school"].set("")
        self.vars["regular_day"].set("Monday")
        self.vars["start_time"].set("09:00")
        self.vars["end_time"].set("10:00")
        self.vars["hours"].set("1.0")
        self.vars["rate"].set("0.00")
        self.vars["mileage"].set("0")

    def _calc_hours(self) -> None:
        try:
            hours = compute_hours(self.vars["start_time"].get(),
                                  self.vars["end_time"].get())
        except ValueError:
            messagebox.showerror("Invalid time", "Use HH:MM (e.g. 09:30).")
            return
        self.vars["hours"].set(f"{hours:g}")

    def _validate(self) -> Client | None:
        description = self.vars["description"].get().strip()
        if not description:
            messagebox.showerror("Missing data", "Description is required.")
            return None
        try:
            parse_time(self.vars["start_time"].get())
            parse_time(self.vars["end_time"].get())
        except ValueError:
            messagebox.showerror("Invalid time", "Times must be HH:MM.")
            return None
        try:
            hours = float(self.vars["hours"].get())
            rate = float(self.vars["rate"].get())
            mileage = float(self.vars["mileage"].get() or 0)
        except ValueError:
            messagebox.showerror("Invalid number",
                                 "Hours, rate, and mileage must be numbers.")
            return None

        return Client(
            description=description,
            school=self.vars["school"].get().strip(),
            regular_day=self.vars["regular_day"].get(),
            start_time=self.vars["start_time"].get().strip(),
            end_time=self.vars["end_time"].get().strip(),
            hours=hours,
            rate=rate,
            mileage=mileage,
            id=self._current_id or Client(description=description).id,
        )

    def _save(self) -> None:
        client = self._validate()
        if client is None:
            return
        self.storage.save_client(client)
        self._current_id = client.id
        self.refresh()
        self.tree.selection_set(client.id)
        self.on_change()

    def _delete(self) -> None:
        if not self._current_id:
            messagebox.showinfo("Nothing selected",
                                "Select a client to delete.")
            return
        if not messagebox.askyesno("Confirm delete",
                                   "Delete this potential visit?"):
            return
        self.storage.delete_client(self._current_id)
        self.clear_form()
        self.refresh()
        self.on_change()
