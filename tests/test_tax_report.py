import pytest
from datetime import date

from timetracker.models import VisitRecord
from timetracker.storage import Storage
from timetracker import tax_report as tax_mod


@pytest.fixture
def store(tmp_path):
    return Storage(tmp_path)


def test_uk_tax_year_range():
    start, end = tax_mod.uk_tax_year_range(2026)
    assert start == date(2026, 4, 6)
    assert end == date(2027, 4, 5)


def test_tax_year_month_keys():
    keys = tax_mod.tax_year_month_keys(2026)
    assert keys[0] == "2026-04"
    assert keys[-1] == "2027-04"
    assert len(keys) == 13


def test_april_boundary_excludes_and_includes(store):
    store.save_record(VisitRecord(
        client_id="c", date="2026-04-05", hours=1, rate=100, mileage=10))
    store.save_record(VisitRecord(
        client_id="c", date="2026-04-06", hours=1, rate=100, mileage=5))
    summary = tax_mod.build_tax_year_summary(store, 2026)
    assert summary.total_payments == 100.0
    assert summary.total_mileage == 5.0


def test_end_april_boundary(store):
    store.save_record(VisitRecord(
        client_id="c", date="2027-04-05", hours=2, rate=50, mileage=8))
    store.save_record(VisitRecord(
        client_id="c", date="2027-04-06", hours=2, rate=50, mileage=20))
    summary = tax_mod.build_tax_year_summary(store, 2026)
    assert summary.total_payments == 100.0
    assert summary.total_mileage == 8.0


def test_spans_two_calendar_years(store):
    store.save_record(VisitRecord(
        client_id="c", date="2026-12-15", hours=1, rate=60, mileage=12))
    store.save_record(VisitRecord(
        client_id="c", date="2027-03-10", hours=2, rate=40, mileage=24))
    summary = tax_mod.build_tax_year_summary(store, 2026)
    assert summary.total_payments == 140.0
    assert summary.total_mileage == 36.0


def test_monthly_breakdown(store):
    store.save_record(VisitRecord(
        client_id="c", date="2026-05-01", hours=1, rate=100, mileage=10))
    store.save_record(VisitRecord(
        client_id="c", date="2026-06-01", hours=2, rate=50, mileage=5))
    summary = tax_mod.build_tax_year_summary(store, 2026)
    by_key = {r.month_key: r for r in summary.rows}
    assert by_key["2026-04"].payments == 0.0
    assert by_key["2026-05"].payments == 100.0
    assert by_key["2026-05"].mileage == 10.0
    assert by_key["2026-06"].payments == 100.0
    assert by_key["2026-06"].mileage == 5.0


def test_empty_months_show_zero(store):
    summary = tax_mod.build_tax_year_summary(store, 2026)
    assert len(summary.rows) == 13
    assert all(r.payments == 0.0 and r.mileage == 0.0 for r in summary.rows)


def test_render_text_includes_totals(store):
    store.save_record(VisitRecord(
        client_id="c", date="2026-05-01", hours=1, rate=100, mileage=10))
    summary = tax_mod.build_tax_year_summary(store, 2026)
    text = tax_mod.render_text(summary)
    assert "2026/27" in text
    assert "TOTAL" in text
    assert "£100.00" in text


def test_suggest_tax_years_from_data(store):
    store.save_record(VisitRecord(
        client_id="c", date="2026-07-01", hours=1, rate=20))
    store.save_record(VisitRecord(
        client_id="c", date="2027-02-01", hours=1, rate=20))
    years = tax_mod.suggest_tax_years(store)
    assert 2026 in years
    assert years == sorted(years, reverse=True)
