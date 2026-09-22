"""Даты в часовом поясе компании (п. 7.6 ТЗ): хранение в UTC, календарные дни — по компании."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def company_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().company_timezone)


def company_today() -> date:
    return datetime.now(company_tz()).date()


def _day_start_utc(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=company_tz()).astimezone(UTC)


def company_day_bounds(
    date_from: date | None, date_to: date | None
) -> tuple[datetime | None, datetime | None]:
    """Период «с — по» включительно в днях компании → полуинтервал [start, end) в UTC."""
    start = _day_start_utc(date_from) if date_from is not None else None
    end = _day_start_utc(date_to + timedelta(days=1)) if date_to is not None else None
    return start, end
