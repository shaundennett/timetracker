"""Domain models for the time tracker.

Two objects:

Client
    A *regular, potential visit* the teacher performs — e.g. "Maths support,
    Oakwood School, every Tuesday 09:00-10:30". These are defined once and
    reused. They carry the default day/time/rate so recording an actual visit
    is mostly a confirm-and-save.

VisitRecord
    An *actual visit that happened* on a specific date. It references the
    Client it came from but snapshots the billing-relevant fields (description,
    school, hours, rate) at the moment of recording. Snapshotting means editing
    a Client's rate later never silently rewrites past invoices.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, time


# Days offered when defining a client's regular slot. Kept here so the UI and
# any validation share one source of truth.
WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

TIME_FORMAT = "%H:%M"
DATE_FORMAT = "%Y-%m-%d"  # Stored form: ISO text sorts in date order.
DISPLAY_DATE_FORMAT = "%d/%m/%Y"  # Shown to the user (UK order).


def _new_id() -> str:
    """Return a short, unique id used as a stable primary key."""
    return uuid.uuid4().hex[:12]


def parse_time(value: str) -> time:
    """Parse a 'HH:MM' string into a time, raising ValueError if malformed."""
    return datetime.strptime(value.strip(), TIME_FORMAT).time()


def format_display_date(value: str) -> str:
    """Turn a stored 'YYYY-MM-DD' string into 'DD/MM/YYYY' for display.

    Text that is not a valid stored date is returned unchanged so rendering
    never fails on unexpected input.
    """
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).strftime(
            DISPLAY_DATE_FORMAT)
    except ValueError:
        return value


def parse_display_date(value: str) -> date:
    """Parse a 'DD/MM/YYYY' string into a date, raising ValueError if bad."""
    return datetime.strptime(value.strip(), DISPLAY_DATE_FORMAT).date()


def compute_hours(start: str, end: str) -> float:
    """Hours between two 'HH:MM' strings, rounded to 2dp.

    Assumes end is later than start on the same day (the common case for a
    single visit). Returns 0.0 if end is not after start.
    """
    s = parse_time(start)
    e = parse_time(end)
    minutes = (e.hour * 60 + e.minute) - (s.hour * 60 + s.minute)
    if minutes <= 0:
        return 0.0
    return round(minutes / 60.0, 2)


@dataclass
class Client:
    """A reusable definition of a regular visit."""

    description: str
    school: str = ""
    regular_day: str = "Monday"
    start_time: str = "09:00"
    end_time: str = "10:00"
    hours: float = 1.0
    rate: float = 0.0
    mileage: float = 0.0  # default round-trip miles; pre-fills a visit
    id: str = field(default_factory=_new_id)

    @property
    def amount(self) -> float:
        """Default charge for one visit (hours * rate), rounded to 2dp."""
        return round(self.hours * self.rate, 2)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Client":
        # Only pull known fields so older/newer files degrade gracefully.
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)


@dataclass
class BusinessProfile:
    """The sole-trader's own details — the "From" block on every invoice.

    Stored once (see Storage.load_business/save_business) and reused. Missing
    fields simply don't render, so a partial profile still produces a usable
    invoice.
    """

    full_name: str = ""
    business_name: str = ""
    utr: str = ""  # Unique Taxpayer Reference
    telephone: str = ""
    email: str = ""
    address: str = ""  # multi-line; newlines preserved on the invoice

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BusinessProfile":
        # Back-compat: an older file stored the UTR under "vat_reference".
        if "utr" not in data and "vat_reference" in data:
            data = {**data, "utr": data["vat_reference"]}
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)


@dataclass
class VisitRecord:
    """A single visit that actually took place, ready for billing."""

    client_id: str
    date: str  # YYYY-MM-DD
    description: str = ""
    school: str = ""
    start_time: str = "09:00"
    end_time: str = "10:00"
    hours: float = 1.0
    rate: float = 0.0
    mileage: float = 0.0  # round-trip miles for this visit (tax use, not billed)
    notes: str = ""
    id: str = field(default_factory=_new_id)

    @property
    def amount(self) -> float:
        return round(self.hours * self.rate, 2)

    @property
    def month_key(self) -> str:
        """The 'YYYY-MM' bucket this record belongs to (its monthly file)."""
        return self.date[:7]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VisitRecord":
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)

    @classmethod
    def from_client(cls, client: Client, date: str) -> "VisitRecord":
        """Build a pre-filled record from a client for a given date.

        The UI presents these values for confirmation/adjustment before saving.
        """
        return cls(
            client_id=client.id,
            date=date,
            description=client.description,
            school=client.school,
            start_time=client.start_time,
            end_time=client.end_time,
            hours=client.hours,
            rate=client.rate,
            mileage=client.mileage,
        )
