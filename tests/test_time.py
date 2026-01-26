from datetime import date

from src.utils.time import hst_day_bounds_to_utc


def test_hst_day_bounds_to_utc():
    start_utc, end_utc = hst_day_bounds_to_utc(date(2026, 1, 26))
    assert start_utc.isoformat() == "2026-01-26T10:00:00"
    assert end_utc.isoformat() == "2026-01-27T10:00:00"
