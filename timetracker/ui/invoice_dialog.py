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
from ..models import PERIOD_MONTH, PERIOD_WEEK, Settings, VisitRecord
from ..periods import Period, month_of, shift, week_of
from ..storage import Storage
from .date_picker import DatePicker
from .style import ACCENT, BORDER, INK, SURFACE

_ALL_SCHOOLS = "All schools"
_MONTHS = list(calendar.month_name)[1:]  # ["January", ..., "December"]


class InvoiceDialog(tk.Toplevel):
    def __init__(self, parent, storage: Storage,
                 default_date: _dt.date | None = None):
        super().__init__(parent)
        self.storage = storage
        self.business = storage.load_business()
        # Month or week billing; the same saved setting as the entry screen.
        self.period_kind = tk.StringVar(
            value=storage.load_settings().period_kind)

        self.title("Create invoice")
        self.transient(parent)
        self.minsize(860, 540)
        self.geometry("980x620")

        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Create invoice",
                  style="Heading.TLabel").grid(row=0, column=0, columnspan=2,
                                               sticky="w")
        ttk.Label(outer, text="Bill a month or a week of visits — save to PDF or print.",
                  style="SubHeading.TLabel").grid(row=1, column=0, columnspan=2,
                                                  sticky="w", pady=(0, 12))
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(1, weight=1)

        # Seed the month and the week from the date on the entry screen.
        start = default_date or _dt.date.today()
        self._week_anchor = start

        self._build_controls(outer, start.year, start.month)
        self._build_preview(outer)

        self._show_mode()
        self._on_period_change()

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
        ttk.Label(panel, text="Bill by").grid(row=r, column=0, sticky="w",
                                              pady=5)
        kind_row = ttk.Frame(panel)
        kind_row.grid(row=r, column=1, sticky="w", pady=5)
        for text, value in (("Month", PERIOD_MONTH), ("Week", PERIOD_WEEK)):
            ttk.Radiobutton(kind_row, text=text, value=value,
                            variable=self.period_kind,
                            command=self._on_kind_change).pack(side="left",
                                                               padx=(0, 10))
        r += 1

        year_label = ttk.Label(panel, text="Year")
        year_label.grid(row=r, column=0, sticky="w", pady=5)
        this_year = _dt.date.today().year
        years = [str(y) for y in range(this_year - 6, this_year + 2)]
        if str(year) not in years:
            years = sorted({*years, str(year)})
        self.year_var = tk.StringVar(value=str(year))
        year_combo = ttk.Combobox(panel, textvariable=self.year_var,
                                  state="readonly", width=16, values=years)
        year_combo.grid(row=r, column=1, sticky="w", pady=5)
        year_combo.bind("<<ComboboxSelected>>",
                        lambda _e: self._on_period_change())
        r += 1

        month_label = ttk.Label(panel, text="Month")
        month_label.grid(row=r, column=0, sticky="w", pady=5)
        self.month_var = tk.StringVar(value=_MONTHS[month - 1])
        month_combo = ttk.Combobox(panel, textvariable=self.month_var,
                                   state="readonly", width=16, values=_MONTHS)
        month_combo.grid(row=r, column=1, sticky="w", pady=5)
        month_combo.bind("<<ComboboxSelected>>",
                         lambda _e: self._on_period_change())
        # Week mode swaps these for the week stepper (see _show_mode).
        self._month_widgets = [year_label, year_combo, month_label,
                               month_combo]
        year_row = r - 1
        r += 1

        week_label = ttk.Label(panel, text="Week")
        week_label.grid(row=year_row, column=0, sticky="w", pady=5)
        week_row = ttk.Frame(panel)
        week_row.grid(row=year_row, column=1, sticky="w", pady=5)
        ttk.Button(week_row, text="◀", width=3,
                   command=lambda: self._step_week(-1)).pack(side="left")
        self.week_text = tk.StringVar()
        ttk.Label(week_row, textvariable=self.week_text, width=34,
                  anchor="center").pack(side="left", padx=4)
        ttk.Button(week_row, text="▶", width=3,
                   command=lambda: self._step_week(1)).pack(side="left")
        self._week_widgets = [week_label, week_row]

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

    def _period(self) -> Period:
        if self.period_kind.get() == PERIOD_WEEK:
            return week_of(self._week_anchor)
        year = int(self.year_var.get())
        month = _MONTHS.index(self.month_var.get()) + 1
        return month_of(_dt.date(year, month, 1))

    def _period_records(self) -> list[VisitRecord]:
        period = self._period()
        return self.storage.list_records_between(period.start, period.end)

    def _show_mode(self) -> None:
        """Show the month boxes or the week stepper, whichever is active."""
        week = self.period_kind.get() == PERIOD_WEEK
        for w in self._month_widgets:
            (w.grid_remove if week else w.grid)()
        for w in self._week_widgets:
            (w.grid if week else w.grid_remove)()

    def _on_kind_change(self) -> None:
        kind = self.period_kind.get()
        self.storage.save_settings(Settings(period_kind=kind))
        if kind == PERIOD_WEEK:
            # Start on today's week if it is in the chosen month, else its 1st.
            chosen = month_of(_dt.date(
                int(self.year_var.get()),
                _MONTHS.index(self.month_var.get()) + 1, 1))
            today = _dt.date.today()
            self._week_anchor = today if chosen.contains(today) else chosen.start
        else:
            self.year_var.set(str(self._week_anchor.year))
            self.month_var.set(_MONTHS[self._week_anchor.month - 1])
        self._show_mode()
        self._on_period_change()

    def _step_week(self, steps: int) -> None:
        self._week_anchor = shift(week_of(self._week_anchor), steps).start
        self._on_period_change()

    def _on_period_change(self) -> None:
        """Period changed: refresh school list, suggested number, preview."""
        period = self._period()
        self.week_text.set(f"Week {period.iso_week[1]}: {period.range_label}")
        records = self._period_records()
        schools = [_ALL_SCHOOLS] + inv_mod.schools_in(records)
        self.school_combo["values"] = schools
        if self.school_var.get() not in schools:
            self.school_var.set(_ALL_SCHOOLS)
        self.number_var.set(inv_mod.suggest_number_for_period(period))
        self._render_preview()

    def _selected_items(self) -> list[VisitRecord]:
        records = self._period_records()
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
            period=self._period().label,
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
