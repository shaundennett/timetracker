"""Dialog for creating and managing roles."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, messagebox
from typing import Callable

from ..roles import RoleManager
from .style import ACCENT, current_accent, readable_fg

# Preset accent colours offered for a role (the first is the app default).
PALETTE = [ACCENT, "#7c5cbf", "#3f7fd1", "#1f9d8f", "#4c9a2a", "#d98a1f",
           "#d9534f", "#5f6b7a"]


class ColorSwatches(tk.Frame):
    """A row of preset colour swatches plus a Custom... picker.

    ``color`` holds the chosen ``#rrggbb`` value, or "" for the default accent.
    """

    def __init__(self, parent: tk.Misc, color: str = ""):
        super().__init__(parent)
        self.color = color
        self._buttons: dict[str, tk.Button] = {}

        for i, swatch in enumerate(PALETTE):
            btn = tk.Button(self, width=2, bg=swatch, activebackground=swatch,
                            command=lambda c=swatch: self.set_color(c))
            btn.grid(row=0, column=i, padx=2)
            self._buttons[swatch] = btn

        tk.Button(self, text="Custom…", command=self._pick_custom).grid(
            row=0, column=len(PALETTE), padx=(8, 0))
        self._refresh()

    def set_color(self, color: str) -> None:
        # The default accent is stored as "" so it keeps following the theme.
        self.color = "" if color.lower() == ACCENT else color.lower()
        self._refresh()

    def _pick_custom(self) -> None:
        _rgb, hex_value = colorchooser.askcolor(
            color=self.color or ACCENT, parent=self.winfo_toplevel(),
            title="Choose role colour")
        if hex_value:
            self.set_color(hex_value)

    def _refresh(self) -> None:
        selected = self.color or ACCENT
        for swatch, btn in self._buttons.items():
            btn.configure(relief="sunken" if swatch == selected else "raised",
                          borderwidth=3 if swatch == selected else 1)


class RoleDialog(tk.Toplevel):
    """Modal dialog for creating a new role.

    Allows the user to name the role and optionally copy the business profile
    from an existing role.
    """

    _NO_COPY = "__none__"

    def __init__(
        self,
        parent: tk.Tk,
        role_manager: RoleManager,
        on_role_created: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)
        self.role_manager = role_manager
        self.on_role_created = on_role_created
        self.new_role = None

        self.title("New Role")
        self.geometry("440x340")
        self.transient(parent)
        self.grab_set()

        # Build the form.
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Role name.
        tk.Label(frame, text="Role name:", font=("TkDefaultFont", 10)).pack(
            anchor="w", pady=(0, 5)
        )
        self.name_var = tk.StringVar()
        self.name_entry = tk.Entry(frame, textvariable=self.name_var, width=40)
        self.name_entry.pack(anchor="w", pady=(0, 15))
        self.name_entry.focus()

        # Business profile copy option.
        tk.Label(
            frame, text="Copy business profile from:", font=("TkDefaultFont", 10)
        ).pack(anchor="w", pady=(0, 5))

        # Non-empty sentinel: Tk treats "" as the radiobutton tristate value,
        # which makes every button in the group look selected.
        self.copy_from_var = tk.StringVar(value=self._NO_COPY)
        option_frame = tk.Frame(frame)
        option_frame.pack(anchor="w", pady=(0, 15))

        tk.Radiobutton(
            option_frame,
            text="Start with empty business profile",
            variable=self.copy_from_var,
            value=self._NO_COPY,
        ).pack(anchor="w")

        roles = self.role_manager.list_roles()
        for role in roles:
            tk.Radiobutton(
                option_frame,
                text=f"Copy from {role.name}",
                variable=self.copy_from_var,
                value=role.id,
            ).pack(anchor="w")

        # Accent colour.
        tk.Label(frame, text="Colour:", font=("TkDefaultFont", 10)).pack(
            anchor="w", pady=(0, 5)
        )
        self.swatches = ColorSwatches(frame)
        self.swatches.pack(anchor="w", pady=(0, 15))

        # Buttons.
        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="e", pady=(15, 0))

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=10,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="Create",
            command=self._on_create,
            bg=current_accent(),
            fg=readable_fg(current_accent()),
            width=10,
        ).pack(side="left")

    def _on_create(self) -> None:
        """Handle Create button click."""
        name = self.name_var.get().strip()

        # Validate and create.
        try:
            new_role = self.role_manager.create_role(name, self.swatches.color)
        except ValueError as e:
            tk.messagebox.showerror("Invalid role name", str(e))
            return

        # Copy business profile if requested.
        copy_from_id = self.copy_from_var.get()
        if copy_from_id != self._NO_COPY:
            source_storage = self.role_manager.storage_for(copy_from_id)
            dest_storage = self.role_manager.storage_for(new_role.id)

            source_profile = source_storage.load_business()
            dest_storage.save_business(source_profile)

        # Notify and close.
        if self.on_role_created:
            self.on_role_created(new_role.id)
        self.destroy()


class RenameRoleDialog(tk.Toplevel):
    """Modal dialog for renaming a role."""

    def __init__(
        self,
        parent: tk.Tk,
        role_manager: RoleManager,
        role_id: str,
        on_renamed: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self.role_manager = role_manager
        self.role_id = role_id
        self.on_renamed = on_renamed

        role = next((r for r in role_manager.list_roles() if r.id == role_id), None)
        if not role:
            self.destroy()
            return

        self.title(f"Rename Role: {role.name}")
        self.geometry("400x150")
        self.transient(parent)
        self.grab_set()

        # Build the form.
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="New name:", font=("TkDefaultFont", 10)).pack(
            anchor="w", pady=(0, 5)
        )
        self.name_var = tk.StringVar(value=role.name)
        self.name_entry = tk.Entry(frame, textvariable=self.name_var, width=40)
        self.name_entry.pack(anchor="w", pady=(0, 15))
        self.name_entry.focus()
        self.name_entry.select_range(0, "end")

        # Buttons.
        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="e", pady=(15, 0))

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=10,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="Rename",
            command=self._on_rename,
            bg=current_accent(),
            fg=readable_fg(current_accent()),
            width=10,
        ).pack(side="left")

    def _on_rename(self) -> None:
        """Handle Rename button click."""
        new_name = self.name_var.get().strip()

        try:
            self.role_manager.rename_role(self.role_id, new_name)
        except ValueError as e:
            messagebox.showerror("Invalid name", str(e))
            return

        if self.on_renamed:
            self.on_renamed()
        self.destroy()


class RoleColorDialog(tk.Toplevel):
    """Modal dialog for changing a role's accent colour."""

    def __init__(
        self,
        parent: tk.Tk,
        role_manager: RoleManager,
        role_id: str,
        on_changed: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self.role_manager = role_manager
        self.role_id = role_id
        self.on_changed = on_changed

        role = next((r for r in role_manager.list_roles() if r.id == role_id), None)
        if not role:
            self.destroy()
            return

        self.title(f"Role Colour: {role.name}")
        self.geometry("440x170")
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(frame, text="Colour:", font=("TkDefaultFont", 10)).pack(
            anchor="w", pady=(0, 5)
        )
        self.swatches = ColorSwatches(frame, role.color)
        self.swatches.pack(anchor="w", pady=(0, 15))

        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="e", pady=(15, 0))

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=10,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="Save",
            command=self._on_save,
            bg=current_accent(),
            fg=readable_fg(current_accent()),
            width=10,
        ).pack(side="left")

    def _on_save(self) -> None:
        """Handle Save button click."""
        try:
            self.role_manager.set_role_color(self.role_id, self.swatches.color)
        except ValueError as e:
            messagebox.showerror("Invalid colour", str(e))
            return

        if self.on_changed:
            self.on_changed()
        self.destroy()


class DeleteRoleDialog(tk.Toplevel):
    """Modal dialog for deleting a role (with confirmation)."""

    def __init__(
        self,
        parent: tk.Tk,
        role_manager: RoleManager,
        role_id: str,
        on_deleted: Callable[[], None] | None = None,
    ):
        super().__init__(parent)
        self.role_manager = role_manager
        self.role_id = role_id
        self.on_deleted = on_deleted

        role = next((r for r in role_manager.list_roles() if r.id == role_id), None)
        if not role:
            self.destroy()
            return

        self.title(f"Delete Role: {role.name}")
        self.geometry("450x200")
        self.transient(parent)
        self.grab_set()

        # Build the form.
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(
            frame,
            text=f"Are you sure you want to delete the role '{role.name}'?",
            font=("TkDefaultFont", 10),
            wraplength=400,
            justify="left",
        ).pack(anchor="w", pady=(0, 15))

        tk.Label(
            frame,
            text="This will permanently delete all data in this role (clients, visits, etc.).\nThis action cannot be undone.",
            font=("TkDefaultFont", 9),
            wraplength=400,
            justify="left",
            fg="red",
        ).pack(anchor="w", pady=(0, 15))

        # Buttons.
        button_frame = tk.Frame(frame)
        button_frame.pack(anchor="e", pady=(15, 0))

        tk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=10,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            button_frame,
            text="Delete",
            command=self._on_delete,
            bg="red",
            fg="white",
            width=10,
        ).pack(side="left")

    def _on_delete(self) -> None:
        """Handle Delete button click."""
        try:
            self.role_manager.delete_role(self.role_id)
        except ValueError as e:
            messagebox.showerror("Cannot delete role", str(e))
            return

        if self.on_deleted:
            self.on_deleted()
        self.destroy()
