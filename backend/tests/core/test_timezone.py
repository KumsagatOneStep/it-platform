from datetime import UTC, date, datetime

from app.core.timezone import company_day_bounds


def test_company_day_bounds_in_utc() -> None:
    # Europe/Moscow = UTC+3: сутки 22.09 по Москве — с 21.09 21:00 до 22.09 21:00 UTC.
    start, end = company_day_bounds(date(2026, 9, 22), date(2026, 9, 22))

    assert start == datetime(2026, 9, 21, 21, 0, tzinfo=UTC)
    assert end == datetime(2026, 9, 22, 21, 0, tzinfo=UTC)


def test_company_day_bounds_open_ends() -> None:
    assert company_day_bounds(None, None) == (None, None)
