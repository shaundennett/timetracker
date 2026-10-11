"""Main application window.

A single data-entry screen (the Record tab) fills the window. Managing the
reusable "potential visit" definitions, editing your business details, and
generating invoices all happen in separate dialogs, reached from the menu bar
or the toolbar, so the day-to-day screen stays focused on recording visits.
"""

from __future__ import annotations

import tkinter as tk

from ..roles import RoleManager
from ..storage import Storage
from .about_dialog import AboutDialog
from .business_dialog import BusinessDialog
from .clients_dialog import ClientsDialog
from .invoice_dialog import InvoiceDialog
from .record_tab import RecordTab
from .role_dialog import RoleDialog, RenameRoleDialog, DeleteRoleDialog
from .style import apply_theme
from .tax_year_dialog import TaxYearDialog


class App(tk.Tk):
    def __init__(self, role_manager: RoleManager | None = None, storage: Storage | None = None):
        super().__init__()
        # Support both role_manager (new) and storage (legacy for testing).
        if role_manager is not None:
            self.role_manager = role_manager
            self.storage = self.role_manager.active_storage()
        elif storage is not None:
            self.role_manager = None
            self.storage = storage
        else:
            self.role_manager = RoleManager()
            self.storage = self.role_manager.active_storage()

        self._update_window_title()
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

    def _update_window_title(self) -> None:
        """Update the window title to show the active role (if multi-role enabled)."""
        if self.role_manager:
            active = self.role_manager.active_role()
            self.title(f"Time Tracker — {active.name}")
        else:
            self.title("Time Tracker")

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

        # Add Role menu if using RoleManager.
        if self.role_manager:
            self._role_menu = tk.Menu(menubar, tearoff=0)
            self._rebuild_role_menu()
            menubar.add_cascade(label="Role", menu=self._role_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About Time Tracker",
                              command=self.open_about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _rebuild_role_menu(self) -> None:
        """Rebuild the Role menu with current roles and active indicator."""
        if not self.role_manager:
            return

        self._role_menu.delete(0, "end")
        active = self.role_manager.active_role()

        # Add radio items for each role.
        for role in self.role_manager.list_roles():
            self._role_menu.add_radiobutton(
                label=role.name,
                value=role.id,
                command=lambda rid=role.id: self.switch_role(rid),
                variable=tk.StringVar(value=active.id),
            )

        self._role_menu.add_separator()
        self._role_menu.add_command(label="New role…",
                                     command=self.open_new_role_dialog)
        self._role_menu.add_command(label="Rename active role…",
                                     command=self.open_rename_role_dialog)
        self._role_menu.add_command(label="Delete active role…",
                                     command=self.open_delete_role_dialog)

    def switch_role(self, role_id: str) -> None:
        """Switch to a different role and rebuild the UI."""
        if not self.role_manager or self.role_manager.active_role().id == role_id:
            return

        self.role_manager.set_active(role_id)
        self.storage = self.role_manager.active_storage()
        self._update_window_title()

        # Rebuild the record tab with the new storage.
        self.record_tab.destroy()
        self.record_tab = RecordTab(
            self, self.storage,
            on_manage_events=self.open_events_dialog,
            on_business=self.open_business_dialog,
            on_invoice=self.open_invoice_dialog,
            on_tax_year=self.open_tax_year_dialog,
        )
        self.record_tab.pack(fill="both", expand=True)

        # Update the role menu checkmark.
        self._rebuild_role_menu()

    def open_events_dialog(self) -> None:
        # The dialog refreshes the entry screen's event picker on every change.
        ClientsDialog(self, self.storage,
                      on_change=self.record_tab.refresh_clients)

    def open_business_dialog(self) -> None:
        BusinessDialog(self, self.storage)

    def open_invoice_dialog(self) -> None:
        InvoiceDialog(self, self.storage,
                      default_date=self.record_tab.current_date())

    def open_tax_year_dialog(self) -> None:
        TaxYearDialog(self, self.storage)

    def open_about_dialog(self) -> None:
        AboutDialog(self)

    def open_new_role_dialog(self) -> None:
        """Open the dialog to create a new role."""
        if self.role_manager:
            RoleDialog(self, self.role_manager,
                      on_role_created=self._on_role_created)

    def _on_role_created(self, role_id: str) -> None:
        """Callback when a new role is created: rebuild menu and switch to it."""
        self._rebuild_role_menu()
        self.switch_role(role_id)

    def open_rename_role_dialog(self) -> None:
        """Open the dialog to rename the active role."""
        if self.role_manager:
            RenameRoleDialog(self, self.role_manager,
                           self.role_manager.active_role().id,
                           on_renamed=self._on_role_renamed)

    def open_delete_role_dialog(self) -> None:
        """Open the dialog to delete the active role."""
        if self.role_manager:
            DeleteRoleDialog(self, self.role_manager,
                           self.role_manager.active_role().id,
                           on_deleted=self._on_role_deleted)

    def _on_role_renamed(self) -> None:
        """Callback when a role is renamed: rebuild menu and update title."""
        self._update_window_title()
        self._rebuild_role_menu()

    def _on_role_deleted(self) -> None:
        """Callback when a role is deleted: switch to first available role."""
        if self.role_manager:
            roles = self.role_manager.list_roles()
            if roles:
                self.switch_role(roles[0].id)
            else:
                # Should not happen (can't delete the last role), but be safe.
                self._rebuild_role_menu()


def run() -> None:
    """Launch the GUI event loop."""
    App().mainloop()
