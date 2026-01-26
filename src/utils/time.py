import os
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

HST_TZ = ZoneInfo("Pacific/Honolulu")


def get_timezone() -> ZoneInfo:
    tz_name = os.getenv("TIMEZONE")
    if tz_name:
        return ZoneInfo(tz_name)
    return HST_TZ


def today_local_date() -> date:
    tz = get_timezone()
    return datetime.now(tz).date()


def parse_date_arg(date_str: Optional[str]) -> date:
    if not date_str:
        return today_local_date()
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def parse_hst_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def normalize_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=HST_TZ)
    return dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def hst_day_bounds_to_utc(report_date: date) -> tuple[datetime, datetime]:
    start_hst = datetime.combine(report_date, datetime.min.time(), tzinfo=HST_TZ)
    next_day_hst = datetime.combine(
        report_date, datetime.min.time(), tzinfo=HST_TZ
    ) + timedelta(days=1)
    start_utc = start_hst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    next_day_utc = next_day_hst.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    return start_utc, next_day_utc
