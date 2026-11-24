from datetime import date

from app.pipeline import parse_date, parse_decimal


def test_iso_date():
    assert parse_date("2026-07-23") == date(2026, 7, 23)


def test_dd_mm_dash_date():
    assert parse_date("25-07-2026") == date(2026, 7, 25)


def test_dd_mm_slash_date():
    assert parse_date("21/05/2026") == date(2026, 5, 21)


def test_mm_dd_slash_date():
    assert parse_date("09/21/2026") == date(2026, 9, 21)


def test_ambiguous_slash_date_uses_us_convention():
    assert parse_date("05/07/2026") == date(2026, 5, 7)


def test_decimal_parser():
    assert parse_decimal("7471.5", "total_value") == 7471.5
