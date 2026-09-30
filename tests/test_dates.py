"""Tests de ui/dates.py : les dates écrites en français."""

import datetime

from ui.dates import day_label, day_title, meals_title, numeric_date, picked_date, week_label

TODAY = datetime.date(2026, 9, 30)  # un mercredi


def test_day_label_and_title():
    assert day_label(TODAY, TODAY) == "aujourd'hui"
    assert day_title(TODAY, TODAY) == "Aujourd'hui"
    assert day_title(datetime.date(2026, 9, 29), TODAY) == "Hier"
    assert day_title(datetime.date(2026, 9, 22), TODAY) == "Mardi 22 septembre"


def test_meals_title():
    assert meals_title(TODAY, TODAY) == "Repas du jour"
    assert meals_title(datetime.date(2026, 9, 29), TODAY) == "Repas d'hier"
    assert meals_title(datetime.date(2026, 9, 22), TODAY) == "Repas du mardi 22 septembre"


def test_numeric_date():
    assert numeric_date(datetime.date(2026, 9, 3)) == "03/09/2026"


def test_week_label_across_months_and_years():
    assert week_label(datetime.date(2026, 9, 21)) == "du 21 au 27 septembre 2026"
    assert week_label(datetime.date(2026, 9, 28)) == "du 28 septembre au 4 octobre 2026"
    assert week_label(datetime.date(2025, 12, 29)) == "du 29 décembre 2025 au 4 janvier 2026"


def test_picked_date_recovers_the_local_day_from_utc():
    utc = datetime.timezone.utc
    day = datetime.date(2026, 9, 23)
    assert picked_date(day) == day
    assert picked_date(datetime.datetime(2026, 9, 22, 22, 0, tzinfo=utc)) == day  # minuit à Paris (UTC+2)
    assert picked_date(datetime.datetime(2026, 9, 23, 4, 0, tzinfo=utc)) == day  # minuit à Montréal (UTC-4)
    assert picked_date(datetime.datetime(2026, 9, 23, 0, 0)) == day  # sans fuseau
