"""UK tax year summary — payments and mileage by month.

The UK tax year runs from 6 April to 5 April the following year. Selecting
tax year *2026* covers 6 April 2026 through 5 April 2027.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, List

from .invoice import CURRENCY

if TYPE_CHECKING:
    from .storage import Storage


@dataclass
class TaxMonthRow:
    """Totals for one calendar month within a tax year."""

    label: str  # e.g. "Apr 2026"
    month_key: str  # e.g. "2026-04"
    payments: float
    mileage: float


@dataclass
class TaxYearSummary:
    """Aggregated payments and mileage for a UK tax year."""

    tax_year: int
    start: date
    end: date
    rows: List[TaxMonthRow] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Display label, e.g. '2026/27'."""
        return f"{self.tax_year}/{self.tax_year + 1 - 2000:02d}"

    @property
    def total_payments(self) -> float:
        return round(sum(r.payments for r in self.rows), 2)

    @property
    def total_mileage(self) -> float:
        return round(sum(r.mileage for r in self.rows), 2)


def uk_tax_year_range(tax_year: int) -> tuple[date, date]:
    """Return (start, end) inclusive for a UK tax year."""
    return date(tax_year, 4, 6), date(tax_year + 1, 4, 5)


def tax_year_month_keys(tax_year: int) -> List[str]:
    """Calendar month keys (YYYY-MM) that overlap a UK tax year, Apr through Mar."""
    keys: List[str] = []
    for m in range(4, 13):
        keys.append(f"{tax_year:04d}-{m:02d}")
    for m in range(1, 4):
        keys.append(f"{tax_year + 1:04d}-{m:02d}")
    # Partial April at the end of the tax year.
    keys.append(f"{tax_year + 1:04d}-04")
    return keys


def _month_label(month_key: str) -> str:
    year, month = (int(p) for p in month_key.split("-"))
    return f"{calendar.month_abbr[month]} {year}"


def _money(value: float) -> str:
    return f"{CURRENCY}{value:,.2f}"


def build_tax_year_summary(storage: Storage, tax_year: int) -> TaxYearSummary:
    """Aggregate visit payments and mileage for a UK tax year."""
    start, end = uk_tax_year_range(tax_year)
    rows: List[TaxMonthRow] = []

    for month_key in tax_year_month_keys(tax_year):
        records = storage.list_records(month_key)
        in_range = [
            r for r in records
            if start <= date.fromisoformat(r.date) <= end
        ]
        rows.append(TaxMonthRow(
            label=_month_label(month_key),
            month_key=month_key,
            payments=round(sum(r.amount for r in in_range), 2),
            mileage=round(sum(r.mileage for r in in_range), 2),
        ))

    return TaxYearSummary(tax_year=tax_year, start=start, end=end, rows=rows)


def suggest_tax_years(storage: Storage) -> List[int]:
    """Tax years that may have data, plus the current tax year, newest first."""
    today = date.today()
    current = today.year if today >= date(today.year, 4, 6) else today.year - 1

    years = {current, current - 1}
    for month_key in storage.available_months():
        year, month = (int(p) for p in month_key.split("-"))
        # Map a calendar month to the tax year it mostly belongs to.
        if month >= 4:
            years.add(year)
        else:
            years.add(year - 1)

    return sorted(years, reverse=True)


def _format_long_date(d: date) -> str:
    return f"{d.day} {calendar.month_name[d.month]} {d.year}"


def render_text(summary: TaxYearSummary, width: int = 74) -> str:
    """Plain-text report for on-screen preview."""
    lines: List[str] = []
    lines.append("=" * width)
    lines.append(f"UK TAX YEAR SUMMARY {summary.label}".center(width))
    period = f"{_format_long_date(summary.start)} – {_format_long_date(summary.end)}"
    lines.append(period.center(width))
    lines.append("=" * width)
    lines.append("")
    lines.append(f"{'Month':<16}{'Payments':>14}{'Mileage':>12}")
    lines.append("-" * width)

    for row in summary.rows:
        miles = f"{row.mileage:g}" if row.mileage else "0"
        lines.append(
            f"{row.label:<16}{_money(row.payments):>14}{miles:>12}"
        )

    lines.append("-" * width)
    total_miles = (
        f"{summary.total_mileage:g}" if summary.total_mileage else "0"
    )
    lines.append(
        f"{'TOTAL':<16}{_money(summary.total_payments):>14}"
        f"{total_miles:>12}"
    )
    lines.append("=" * width)
    return "\n".join(lines)
