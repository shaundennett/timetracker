import pytest

from timetracker.models import (
    Client,
    VisitRecord,
    compute_hours,
    parse_time,
)


def test_compute_hours_basic():
    assert compute_hours("09:00", "10:30") == 1.5
    assert compute_hours("09:00", "10:00") == 1.0


def test_compute_hours_non_positive_returns_zero():
    assert compute_hours("10:00", "09:00") == 0.0
    assert compute_hours("09:00", "09:00") == 0.0


def test_parse_time_invalid_raises():
    with pytest.raises(ValueError):
        parse_time("nope")


def test_client_amount():
    c = Client(description="Maths", hours=2.0, rate=30.0)
    assert c.amount == 60.0


def test_client_roundtrip_and_unknown_fields_ignored():
    c = Client(description="Maths", school="Oakwood", rate=25.0)
    data = c.to_dict()
    data["some_future_field"] = "ignored"
    restored = Client.from_dict(data)
    assert restored.description == "Maths"
    assert restored.school == "Oakwood"
    assert restored.id == c.id
    assert not hasattr(restored, "some_future_field")


def test_visit_month_key():
    r = VisitRecord(client_id="x", date="2026-07-19")
    assert r.month_key == "2026-07"


def test_from_client_snapshots_fields():
    c = Client(description="Maths", school="Oakwood", start_time="09:00",
               end_time="10:30", hours=1.5, rate=40.0, mileage=24)
    r = VisitRecord.from_client(c, "2026-07-21")
    assert r.client_id == c.id
    assert r.date == "2026-07-21"
    assert r.description == "Maths"
    assert r.school == "Oakwood"
    assert r.hours == 1.5
    assert r.rate == 40.0
    assert r.amount == 60.0
    # Mileage pre-fills from the client's default.
    assert r.mileage == 24
    # It's a distinct object with its own id, not the client's.
    assert r.id != c.id


def test_mileage_defaults_to_zero_and_survives_roundtrip():
    assert Client(description="x").mileage == 0.0
    r = VisitRecord(client_id="c", date="2026-07-01", mileage=12.5)
    assert r.mileage == 12.5
    # Unknown/absent mileage in an older file degrades to the 0 default.
    restored = VisitRecord.from_dict({"client_id": "c", "date": "2026-07-01"})
    assert restored.mileage == 0.0
