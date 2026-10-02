"""JSON persistence for clients and visit records.

Design goals:
- No external dependencies (plain JSON on disk).
- Clients live in a single file: ``clients.json``.
- Visit records are split into one file per month: ``time_YYYY-MM.json``.
  Monthly files keep each billing period self-contained and make it obvious
  which data feeds which invoice.

All writes are atomic (write to a temp file, then replace) so an interrupted
save cannot corrupt existing data.

Swap this module out (e.g. for SQLite) without touching the UI, as long as the
method signatures stay the same.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import List

from .models import (
    DATE_FORMAT,
    BusinessProfile,
    Client,
    Settings,
    VisitRecord,
)
from .periods import month_keys_between


class Storage:
    """File-backed store for clients and monthly visit records."""

    def __init__(self, data_dir: str | os.PathLike = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.clients_file = self.data_dir / "clients.json"
        self.business_file = self.data_dir / "business.json"
        self.settings_file = self.data_dir / "settings.json"

    # ------------------------------------------------------------------ #
    # Low-level helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _read_json(path: Path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            # Corrupt or unreadable file: fall back rather than crash the UI.
            return default

    @staticmethod
    def _write_json(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: temp file in the same dir, then os.replace.
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _month_file(self, month_key: str) -> Path:
        """Path to the file holding records for a 'YYYY-MM' month."""
        return self.data_dir / f"time_{month_key}.json"

    # ------------------------------------------------------------------ #
    # Clients (CRUD)
    # ------------------------------------------------------------------ #
    def list_clients(self) -> List[Client]:
        raw = self._read_json(self.clients_file, [])
        clients = [Client.from_dict(item) for item in raw]
        clients.sort(key=lambda c: c.description.lower())
        return clients

    def get_client(self, client_id: str) -> Client | None:
        return next((c for c in self.list_clients() if c.id == client_id), None)

    def save_client(self, client: Client) -> Client:
        """Create or update a client (upsert keyed on id)."""
        clients = self.list_clients()
        for i, existing in enumerate(clients):
            if existing.id == client.id:
                clients[i] = client
                break
        else:
            clients.append(client)
        self._write_json(self.clients_file, [c.to_dict() for c in clients])
        return client

    def delete_client(self, client_id: str) -> None:
        clients = [c for c in self.list_clients() if c.id != client_id]
        self._write_json(self.clients_file, [c.to_dict() for c in clients])

    # ------------------------------------------------------------------ #
    # Business profile (single record, used for invoicing)
    # ------------------------------------------------------------------ #
    def load_business(self) -> BusinessProfile:
        """Return the stored business profile, or an empty one if unset."""
        raw = self._read_json(self.business_file, {})
        return BusinessProfile.from_dict(raw) if raw else BusinessProfile()

    def save_business(self, profile: BusinessProfile) -> BusinessProfile:
        self._write_json(self.business_file, profile.to_dict())
        return profile

    # ------------------------------------------------------------------ #
    # User settings (single record)
    # ------------------------------------------------------------------ #
    def load_settings(self) -> Settings:
        """Return stored preferences, or the defaults if unset/unreadable."""
        raw = self._read_json(self.settings_file, {})
        return Settings.from_dict(raw) if isinstance(raw, dict) else Settings()

    def save_settings(self, settings: Settings) -> Settings:
        self._write_json(self.settings_file, settings.to_dict())
        return settings

    # ------------------------------------------------------------------ #
    # Visit records (stored per month)
    # ------------------------------------------------------------------ #
    def list_records(self, month_key: str) -> List[VisitRecord]:
        raw = self._read_json(self._month_file(month_key), [])
        records = [VisitRecord.from_dict(item) for item in raw]
        records.sort(key=lambda r: (r.date, r.start_time))
        return records

    def list_records_between(self, start: date, end: date) -> List[VisitRecord]:
        """Records dated from ``start`` to ``end`` inclusive, in date order.

        Files are monthly, so a range such as a week can span two of them.
        """
        first, last = start.strftime(DATE_FORMAT), end.strftime(DATE_FORMAT)
        records = [
            r
            for key in month_keys_between(start, end)
            for r in self.list_records(key)
            if first <= r.date <= last  # ISO text compares in date order
        ]
        records.sort(key=lambda r: (r.date, r.start_time))
        return records

    def save_record(self, record: VisitRecord) -> VisitRecord:
        """Create or update a record inside its month's file."""
        records = self.list_records(record.month_key)
        for i, existing in enumerate(records):
            if existing.id == record.id:
                records[i] = record
                break
        else:
            records.append(record)
        self._write_json(
            self._month_file(record.month_key),
            [r.to_dict() for r in records],
        )
        return record

    def delete_record(self, month_key: str, record_id: str) -> None:
        records = [r for r in self.list_records(month_key) if r.id != record_id]
        self._write_json(
            self._month_file(month_key),
            [r.to_dict() for r in records],
        )

    def available_months(self) -> List[str]:
        """All 'YYYY-MM' keys that currently have a data file, newest first."""
        months = [
            p.stem.replace("time_", "")
            for p in self.data_dir.glob("time_*.json")
        ]
        months.sort(reverse=True)
        return months

    def month_total(self, month_key: str) -> float:
        """Total billable amount for a month (sum of record amounts)."""
        return round(sum(r.amount for r in self.list_records(month_key)), 2)
