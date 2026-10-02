"""Main application window.

A single data-entry screen (the Record tab) fills the window. Managing the
reusable "potential visit" definitions, editing your business details, and
generating invoices all happen in separate dialogs, reached from the menu bar
or the toolbar, so the day-to-day screen stays focused on recording visits.
"""

from __future__ import annotations

import tkinter as tk

from ..storage import Storage
from .business_dialog import BusinessDialog
from .clients_dialog import ClientsDialog
from .invoice_dialog import InvoiceDialog
from .record_tab import RecordTab
from .style import apply_theme
from .tax_year_dialog import TaxYearDialog


class App(tk.Tk):
    def __init__(self, storage: Storage | None = None):
        super().__init__()
        self.storage = storage or Storage()

        self.title("Time Tracker")
        self.geometry("1120x720")
        self.minsize(960, 600)

        apply_theme(self)
        self._build_menu()

        self.record_tab = RecordTab(
            self, self.storage,
            on_manage_events=self.open_events_dialog,
            on_business=self.open_business_dialog,
            on_invoice=self.open_invoice_dialog,
            on_tax_year=self.open_tax_year_dialog,
        )
        self.record_tab.pack(fill="both", expand=True)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        events_menu = tk.Menu(menubar, tearoff=0)
        events_menu.add_command(label="Manage potential visits…",
                                command=self.open_events_dialog)
        events_menu.add_command(label="Business details…",
                                command=self.open_business_dialog)
        menubar.add_cascade(label="Events", menu=events_menu)

        invoice_menu = tk.Menu(menubar, tearoff=0)
        invoice_menu.add_command(label="Create invoice…",
                                 command=self.open_invoice_dialog)
        invoice_menu.add_command(label="Tax year summary…",
                                 command=self.open_tax_year_dialog)
        menubar.add_cascade(label="Invoice", menu=invoice_menu)

        self.config(menu=menubar)

    def open_events_dialog(self) -> None:
        # The dialog refreshes the entry screen's event picker on every change.
        ClientsDialog(self, self.storage,
                      on_change=self.record_tab.refresh_clients)

    def open_business_dialog(self) -> None:
        BusinessDialog(self, self.storage)

    def open_invoice_dialog(self) -> None:
        InvoiceDialog(self, self.storage,
                      default_month=self.record_tab.current_month())

    def open_tax_year_dialog(self) -> None:
        TaxYearDialog(self, self.storage)


def run() -> None:
    """Launch the GUI event loop."""
    App().mainloop()
