from datetime import date

import pytest

from timetracker.periods import (
    Period,
    month_keys_between,
    month_of,
    period_for,
    shift,
    week_of,
)


def test_week_runs_monday_to_sunday():
    wk = week_of(date(2026, 7, 8))  # a Wednesday
    assert (wk.start, wk.end) == (date(2026, 7, 6), date(2026, 7, 12))
    assert wk.start.weekday() == 0 and wk.end.weekday() == 6


@pytest.mark.parametrize("day", [date(2026, 7, 6), date(2026, 7, 11),
                                 date(2026, 7, 12)])
def test_every_day_of_the_week_maps_to_the_same_week(day):
    # Monday, Saturday and Sunday all belong to the week commencing 06/07.
    assert week_of(day).start == date(2026, 7, 6)


def test_week_across_a_month_end():
    wk = week_of(date(2026, 7, 1))
    assert (wk.start, wk.end) == (date(2026, 6, 29), date(2026, 7, 5))
    assert wk.month_keys == ["2026-06", "2026-07"]


def test_week_across_a_year_end_uses_the_iso_year():
    wk = week_of(date(2027, 1, 1))
    assert (wk.start, wk.end) == (date(2026, 12, 28), date(2027, 1, 3))
    assert wk.month_keys == ["2026-12", "2027-01"]
    assert wk.iso_week == (2026, 53)


def test_month_boundaries_including_leap_february():
    assert (month_of(date(2028, 2, 10)).start,
            month_of(date(2028, 2, 10)).end) == (date(2028, 2, 1),
                                                 date(2028, 2, 29))
    assert month_of(date(2026, 12, 5)).end == date(2026, 12, 31)
    assert month_of(date(2026, 12, 5)).month_keys == ["2026-12"]


def test_shift_weeks_and_months_across_year_boundaries():
    wk = week_of(date(2026, 12, 30))
    assert shift(wk, 1).start == date(2027, 1, 4)
    assert shift(wk, -1).start == date(2026, 12, 21)
    m = month_of(date(2026, 12, 15))
    assert shift(m, 1).start == date(2027, 1, 1)
    assert shift(shift(m, 1), -1) == m
    assert shift(month_of(date(2026, 1, 31)), -1).start == date(2025, 12, 1)


def test_period_for_and_unknown_kind():
    assert period_for("week", date(2026, 7, 8)) == week_of(date(2026, 7, 8))
    assert period_for("month", date(2026, 7, 8)) == month_of(date(2026, 7, 8))
    with pytest.raises(ValueError):
        period_for("fortnight", date(2026, 7, 8))


def test_labels():
    assert week_of(date(2026, 7, 8)).label == "Week commencing 06/07/2026"
    assert week_of(date(2026, 7, 8)).range_label == "06/07/2026 - 12/07/2026"
    assert month_of(date(2026, 7, 8)).label == "July 2026"


def test_contains_is_inclusive():
    wk = week_of(date(2026, 7, 8))
    assert wk.contains(date(2026, 7, 6)) and wk.contains(date(2026, 7, 12))
    assert not wk.contains(date(2026, 7, 13))


def test_month_keys_between_spans_years():
    assert month_keys_between(date(2026, 11, 30), date(2027, 2, 1)) == [
        "2026-11", "2026-12", "2027-01", "2027-02"]
