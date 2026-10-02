"""Billing/display periods: a calendar month or a Monday-to-Sunday week.

Pure date arithmetic with no UI code, so the entry screen, the invoice dialog
and the storage layer all agree on where a period starts and ends.

A week runs Monday to Sunday and is named by its Monday ("week commencing").
Sunday is included so a weekend visit still belongs to a week and can never be
left off an invoice.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Tuple

from .models import DISPLAY_DATE_FORMAT, PERIOD_MONTH, PERIOD_WEEK


@dataclass(frozen=True)
class Period:
    kind: str  # PERIOD_MONTH or PERIOD_WEEK
    start: date
    end: date  # inclusive

    @property
    def month_keys(self) -> List[str]:
        """The 'YYYY-MM' data files this period can touch."""
        return month_keys_between(self.start, self.end)

    @property
    def label(self) -> str:
        """Short name used in headings and on invoices."""
        if self.kind == PERIOD_WEEK:
            return f"Week commencing {self.start.strftime(DISPLAY_DATE_FORMAT)}"
        return f"{calendar.month_name[self.start.month]} {self.start.year}"

    @property
    def range_label(self) -> str:
        """'06/07/2026 - 12/07/2026' (ASCII hyphen so it is PDF-safe)."""
        return (f"{self.start.strftime(DISPLAY_DATE_FORMAT)} - "
                f"{self.end.strftime(DISPLAY_DATE_FORMAT)}")

    @property
    def iso_week(self) -> Tuple[int, int]:
        """(ISO year, ISO week number). All days of a Mon-Sun week agree."""
        iso = self.start.isocalendar()
        return iso[0], iso[1]

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


def month_keys_between(start: date, end: date) -> List[str]:
    """Every 'YYYY-MM' from start's month to end's month, in order."""
    keys: List[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        keys.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return keys


def month_of(day: date) -> Period:
    last = calendar.monthrange(day.year, day.month)[1]
    return Period(PERIOD_MONTH, day.replace(day=1), day.replace(day=last))


def week_of(day: date) -> Period:
    monday = day - timedelta(days=day.weekday())
    return Period(PERIOD_WEEK, monday, monday + timedelta(days=6))


def period_for(kind: str, day: date) -> Period:
    """The period of the given kind that contains ``day``."""
    if kind == PERIOD_WEEK:
        return week_of(day)
    if kind == PERIOD_MONTH:
        return month_of(day)
    raise ValueError(f"Unknown period kind: {kind!r}")


def shift(period: Period, steps: int) -> Period:
    """The period ``steps`` periods after (or before, if negative) this one."""
    if period.kind == PERIOD_WEEK:
        return week_of(period.start + timedelta(weeks=steps))
    index = period.start.year * 12 + period.start.month - 1 + steps
    return month_of(date(index // 12, index % 12 + 1, 1))
