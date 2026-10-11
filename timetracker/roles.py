"""Role management for multi-role support.

A role is a separate dataset: clients, business profile, visit records, and
settings. Each role is its own subdirectory under the data root. This module
manages the manifest (roles.json) and provides methods to create, list, and
switch between roles.

Design: roles is a thin coordination layer above Storage. Each role gets its own
Storage instance pointed at its subdirectory. This keeps Storage's method
signatures stable and means invoice.py and tax_report.py need no changes.
"""

from __future__ import annotations

import os
import shutil
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import List

from .models import _new_id
from .storage import read_json, write_json, Storage

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _check_color(color: str) -> str:
    """Return a normalised ``#rrggbb`` colour ('' allowed); raise ValueError."""
    color = color.strip()
    if color and not _HEX_COLOR.match(color):
        raise ValueError("Colour must be in #rrggbb format")
    return color.lower()


@dataclass
class Role:
    """A role: an id (stable folder name), a display name and an accent colour.

    ``color`` is a ``#rrggbb`` string; empty means the app's default accent.
    """

    id: str
    name: str
    color: str = ""

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict (empty colour is omitted)."""
        data = asdict(self)
        if not data["color"]:
            del data["color"]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Role":
        """Build a Role, ignoring unknown keys and defaulting missing ones."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


class RoleManager:
    """Manages roles and their data directories.

    Roles are subdirectories of a data root. A manifest (roles.json) at the root
    tracks all roles and which is currently active.
    """

    def __init__(self, data_root: str | os.PathLike = "data"):
        """Initialize the RoleManager.

        On first run (no roles.json), migrate legacy data or bootstrap a default role.
        """
        self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.data_root / "roles.json"
        self._ensure_initialised()

    def _ensure_initialised(self) -> None:
        """Bootstrap or migrate on first run; idempotent."""
        if self.manifest_file.exists():
            try:
                manifest = read_json(self.manifest_file, None)
                if manifest is not None and isinstance(manifest, dict):
                    if "active" in manifest and "roles" in manifest:
                        return  # Valid manifest, we're done
            except Exception:
                pass
            # Manifest exists but is corrupt; recover below.

        # No valid manifest: check for legacy data or fresh install.
        legacy_files = [
            self.data_root / "clients.json",
            self.data_root / "business.json",
            self.data_root / "settings.json",
        ]
        legacy_files += list(self.data_root.glob("time_*.json"))

        if legacy_files:
            # Migrate: copy legacy files into a Default role.
            default_role = Role(id=_new_id(), name="Default")
            role_dir = self.role_dir(default_role.id)
            role_dir.mkdir(parents=True, exist_ok=True)

            for legacy_file in self.data_root.glob("*.json"):
                if legacy_file.name in [
                    "clients.json",
                    "business.json",
                    "settings.json",
                ] or legacy_file.name.startswith("time_"):
                    dest = role_dir / legacy_file.name
                    with open(legacy_file, "r", encoding="utf-8") as src:
                        dest.write_text(src.read(), encoding="utf-8")

            manifest = {"active": default_role.id, "roles": [default_role.to_dict()]}
            write_json(self.manifest_file, manifest)
        else:
            # Fresh install: create one empty Default role.
            default_role = Role(id=_new_id(), name="Default")
            role_dir = self.role_dir(default_role.id)
            role_dir.mkdir(parents=True, exist_ok=True)

            manifest = {"active": default_role.id, "roles": [default_role.to_dict()]}
            write_json(self.manifest_file, manifest)

    def _read_manifest(self) -> dict | None:
        """Read and return the manifest, or None if corrupt."""
        return read_json(self.manifest_file, None)

    def list_roles(self) -> List[Role]:
        """Return all roles, sorted by name."""
        manifest = self._read_manifest()
        if not manifest:
            return []
        roles = [Role.from_dict(r) for r in manifest.get("roles", [])]
        roles.sort(key=lambda r: r.name.lower())
        return roles

    def active_role(self) -> Role:
        """Return the currently active role. Guaranteed to exist after init."""
        manifest = self._read_manifest()
        if not manifest:
            # Corrupt or missing; recover by bootstrapping.
            self._ensure_initialised()
            manifest = self._read_manifest()

        active_id = manifest.get("active") if manifest else None
        roles = (
            [Role.from_dict(r) for r in manifest.get("roles", [])] if manifest else []
        )

        if active_id and any(r.id == active_id for r in roles):
            return next(r for r in roles if r.id == active_id)

        # Active role missing; pick the first or bootstrap.
        if roles:
            return roles[0]
        # Should not happen after _ensure_initialised, but recover anyway.
        self._ensure_initialised()
        return self.active_role()

    def set_active(self, role_id: str) -> None:
        """Set the active role. Raises ValueError if the id does not exist."""
        roles = self.list_roles()
        if not any(r.id == role_id for r in roles):
            raise ValueError(f"Role {role_id} not found")

        manifest = self._read_manifest()
        if manifest:
            manifest["active"] = role_id
            write_json(self.manifest_file, manifest)

    def create_role(self, name: str, color: str = "") -> Role:
        """Create a new empty role with the given name and optional colour.

        Validates that the name is non-empty and not a case-insensitive duplicate,
        and that the colour is ``#rrggbb`` (or empty). Raises ValueError if
        invalid. Does not switch to the new role.
        """
        trimmed = name.strip()
        if not trimmed:
            raise ValueError("Role name cannot be empty")
        color = _check_color(color)

        existing = self.list_roles()
        if any(r.name.lower() == trimmed.lower() for r in existing):
            raise ValueError(f"A role named '{trimmed}' already exists")

        new_role = Role(id=_new_id(), name=trimmed, color=color)
        role_dir = self.role_dir(new_role.id)
        role_dir.mkdir(parents=True, exist_ok=True)

        manifest = self._read_manifest()
        if manifest:
            manifest["roles"].append(new_role.to_dict())
            write_json(self.manifest_file, manifest)

        return new_role

    def rename_role(self, role_id: str, new_name: str) -> Role:
        """Rename a role. Raises ValueError if the new name is invalid or duplicate."""
        trimmed = new_name.strip()
        if not trimmed:
            raise ValueError("Role name cannot be empty")

        roles = self.list_roles()
        target = next((r for r in roles if r.id == role_id), None)
        if not target:
            raise ValueError(f"Role {role_id} not found")

        # Check for duplicates (excluding the role being renamed).
        if any(r.name.lower() == trimmed.lower() and r.id != role_id for r in roles):
            raise ValueError(f"A role named '{trimmed}' already exists")

        target.name = trimmed
        manifest = self._read_manifest()
        if manifest:
            manifest["roles"] = [
                r if r["id"] != role_id else target.to_dict() for r in manifest["roles"]
            ]
            write_json(self.manifest_file, manifest)

        return target

    def set_role_color(self, role_id: str, color: str) -> Role:
        """Set a role's accent colour ('' resets to the default).

        Raises ValueError if the colour is malformed or the role is unknown.
        """
        color = _check_color(color)

        target = next((r for r in self.list_roles() if r.id == role_id), None)
        if not target:
            raise ValueError(f"Role {role_id} not found")

        target.color = color
        manifest = self._read_manifest()
        if manifest:
            manifest["roles"] = [
                r if r["id"] != role_id else target.to_dict() for r in manifest["roles"]
            ]
            write_json(self.manifest_file, manifest)

        return target

    def delete_role(self, role_id: str) -> None:
        """Delete a role and its directory.

        Raises ValueError if the role is the only one, the active one, or not found.
        """
        roles = self.list_roles()
        if len(roles) == 1:
            raise ValueError("Cannot delete the last role")

        target = next((r for r in roles if r.id == role_id), None)
        if not target:
            raise ValueError(f"Role {role_id} not found")

        active = self.active_role()
        if active.id == role_id:
            raise ValueError("Cannot delete the active role")

        # Remove the role directory.
        role_dir = self.role_dir(role_id)
        if role_dir.exists():
            shutil.rmtree(role_dir)

        # Remove from manifest.
        manifest = self._read_manifest()
        if manifest:
            manifest["roles"] = [r for r in manifest["roles"] if r["id"] != role_id]
            write_json(self.manifest_file, manifest)

    def role_dir(self, role_id: str) -> Path:
        """Return the directory path for a given role id."""
        return self.data_root / role_id

    def storage_for(self, role_id: str) -> Storage:
        """Return a Storage instance for the given role."""
        return Storage(self.role_dir(role_id))

    def active_storage(self) -> Storage:
        """Return a Storage instance for the active role."""
        return self.storage_for(self.active_role().id)
