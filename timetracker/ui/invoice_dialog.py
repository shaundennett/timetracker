"""Dialog for generating, previewing, saving, and printing an invoice.

Choose the invoice period by year and month, optionally narrow to one school,
adjust the invoice number, date, and notes, watch the live text preview update,
then Save as PDF or Print.
"""

from __future__ import annotations

import calendar
import datetime as _dt
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import invoice as inv_mod
from ..models import VisitRecord
from ..storage import Storage
from .date_picker import DatePicker
from .style import ACCENT, BORDER, INK, SURFACE

_ALL_SCHOOLS = "All schools"
_MONTHS = list(calendar.month_name)[1:]  # ["January", ..., "December"]


class InvoiceDialog(tk.Toplevel):
    def __init__(self, parent, storage: Storage, default_month: str | None = None):
        super().__init__(parent)
        self.storage = storage
        self.business = storage.load_business()

        self.title("Create invoice")
        self.transient(parent)
        self.minsize(860, 540)
        self.geometry("980x620")

        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Create invoice",
                  style="Heading.TLabel").grid(row=0, column=0, columnspan=2,
                                               sticky="w")
        ttk.Label(outer, text="Bill a month of visits — save to PDF or print.",
                  style="SubHeading.TLabel").grid(row=1, column=0, columnspan=2,
                                                  sticky="w", pady=(0, 12))
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(1, weight=1)

        # Seed year/month from the passed-in default (YYYY-MM) or today.
        today = _dt.date.today()
        year, month = today.year, today.month
        if default_month:
            try:
                year, month = (int(p) for p in default_month.split("-")[:2])
            except (ValueError, TypeError):
                pass

        self._build_controls(outer, year, month)
        self._build_preview(outer)

        self._on_month_change()

        if not self.business.business_name and not self.business.full_name:
            self.after(150, self._warn_no_business)

        self.grab_set()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_controls(self, outer, year: int, month: int) -> None:
        panel = ttk.LabelFrame(outer, text="Invoice options", padding=14)
        panel.grid(row=2, column=0, sticky="nsw", padx=(0, 14))

        r = 0
        ttk.Label(panel, text="Year").grid(row=r, column=0, sticky="w", pady=5)
        this_year = _dt.date.today().year
        years = [str(y) for y in range(this_year - 6, this_year + 2)]
        if str(year) not in years:
            years = sorted({*years, str(year)})
        self.year_var = tk.StringVar(value=str(year))
        year_combo = ttk.Combobox(panel, textvariable=self.year_var,
                                  state="readonly", width=16, values=years)
        year_combo.grid(row=r, column=1, sticky="w", pady=5)
        year_combo.bind("<<ComboboxSelected>>",
                        lambda _e: self._on_month_change())
        r += 1

        ttk.Label(panel, text="Month").grid(row=r, column=0, sticky="w", pady=5)
        self.month_var = tk.StringVar(value=_MONTHS[month - 1])
        month_combo = ttk.Combobox(panel, textvariable=self.month_var,
                                   state="readonly", width=16, values=_MONTHS)
        month_combo.grid(row=r, column=1, sticky="w", pady=5)
        month_combo.bind("<<ComboboxSelected>>",
                         lambda _e: self._on_month_change())
        r += 1

        ttk.Label(panel, text="School").grid(row=r, column=0, sticky="w", pady=5)
        self.school_var = tk.StringVar(value=_ALL_SCHOOLS)
        self.school_combo = ttk.Combobox(panel, textvariable=self.school_var,
                                        state="readonly", width=16)
        self.school_combo.grid(row=r, column=1, sticky="w", pady=5)
        self.school_combo.bind("<<ComboboxSelected>>",
                              lambda _e: self._render_preview())
        r += 1

        ttk.Label(panel, text="Invoice no.").grid(row=r, column=0, sticky="w",
                                                 pady=5)
        self.number_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.number_var, width=18).grid(
            row=r, column=1, sticky="w", pady=5)
        r += 1

        ttk.Label(panel, text="Date").grid(row=r, column=0, sticky="w", pady=5)
        self.date_picker = DatePicker(panel, width=14,
                                      on_change=self._render_preview)
        self.date_picker.grid(row=r, column=1, sticky="w", pady=5)
        r += 1

        ttk.Label(panel, text="Notes").grid(row=r, column=0, sticky="nw", pady=5)
        self.notes = tk.Text(panel, height=4, width=24, wrap="word",
                            relief="solid", borderwidth=1,
                            highlightthickness=1, highlightbackground=BORDER,
                            highlightcolor=ACCENT, background=SURFACE,
                            foreground=INK, insertbackground=INK,
                            padx=6, pady=4, font=("Segoe UI", 10))
        self.notes.grid(row=r, column=1, sticky="ew", pady=5)
        r += 1

        # Recompute the preview whenever these change.
        self.number_var.trace_add("write", lambda *_: self._render_preview())
        self.notes.bind("<KeyRelease>", lambda _e: self._render_preview())

        ttk.Button(panel, text="Refresh preview",
                   command=self._render_preview).grid(row=r, column=0,
                                                      columnspan=2, sticky="ew",
                                                      pady=(12, 0))

    def _build_preview(self, outer) -> None:
        right = ttk.Frame(outer)
        right.grid(row=2, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Preview", style="SubHeading.TLabel").grid(
            row=0, column=0, sticky="w")
        self.preview = tk.Text(right, wrap="none", relief="solid",
                             borderwidth=1, highlightthickness=1,
                             highlightbackground=BORDER, highlightcolor=ACCENT,
                             font=("Consolas", 10), background=SURFACE,
                             foreground=INK, padx=12, pady=10, state="disabled")
        self.preview.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(right, orient="vertical",
                          command=self.preview.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=sb.set)

        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(actions, text="Close", command=self.destroy).pack(
            side="right")
        ttk.Button(actions, text="Print", command=self._print).pack(
            side="right", padx=8)
        ttk.Button(actions, text="Save as PDF…", style="Accent.TButton",
                   command=self._save_pdf).pack(side="right")

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #
    def _warn_no_business(self) -> None:
        messagebox.showinfo(
            "No business details",
            "Your business details are empty, so the invoice header will be "
            "blank.\n\nClose this and use Events ▸ Business details… to fill "
            "them in first.", parent=self)

    def _month_key(self) -> str:
        year = int(self.year_var.get())
        month = _MONTHS.index(self.month_var.get()) + 1
        return f"{year:04d}-{month:02d}"

    def _month_records(self) -> list[VisitRecord]:
        return self.storage.list_records(self._month_key())

    def _on_month_change(self) -> None:
        """Year/month changed: refresh school list, suggested number, preview."""
        records = self._month_records()
        schools = [_ALL_SCHOOLS] + inv_mod.schools_in(records)
        self.school_combo["values"] = schools
        if self.school_var.get() not in schools:
            self.school_var.set(_ALL_SCHOOLS)
        self.number_var.set(inv_mod.suggest_number(self._month_key()))
        self._render_preview()

    def _selected_items(self) -> list[VisitRecord]:
        records = self._month_records()
        school = self.school_var.get()
        if school and school != _ALL_SCHOOLS:
            records = [r for r in records if r.school == school]
        return records

    def _build_invoice(self) -> inv_mod.Invoice:
        return inv_mod.Invoice(
            number=self.number_var.get().strip() or "INV",
            date=self.date_picker.get_date().isoformat(),
            business=self.business,
            items=self._selected_items(),
            notes=self.notes.get("1.0", "end").strip(),
        )

    def _render_preview(self) -> None:
        text = inv_mod.render_text(self._build_invoice())
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    # ------------------------------------------------------------------ #
    # Output
    # ------------------------------------------------------------------ #
    def _save_pdf(self) -> None:
        invoice = self._build_invoice()
        if not invoice.items and not messagebox.askyesno(
                "No visits", "This period has no visits. Save anyway?",
                parent=self):
            return
        default = f"{invoice.number or 'invoice'}.pdf"
        path = filedialog.asksaveasfilename(
            parent=self, title="Save invoice as PDF", defaultextension=".pdf",
            initialfile=default, filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        try:
            inv_mod.render_pdf(invoice, path)
        except Exception as exc:  # pragma: no cover - surfaced to the user
            messagebox.showerror("Could not save PDF", str(exc), parent=self)
            return
        if messagebox.askyesno("Saved", f"Saved to:\n{path}\n\nOpen it now?",
                               parent=self):
            try:
                os.startfile(path)  # type: ignore[attr-defined]
            except (AttributeError, OSError):
                pass

    def _print(self) -> None:
        invoice = self._build_invoice()
        if not invoice.items and not messagebox.askyesno(
                "No visits", "This period has no visits. Print anyway?",
                parent=self):
            return
        try:
            path = inv_mod.render_to_temp(invoice)
            inv_mod.print_pdf(path)
        except Exception as exc:  # pragma: no cover - surfaced to the user
            messagebox.showerror("Could not print", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Printing",
            "The invoice was sent to your default PDF handler for printing.",
            parent=self)
