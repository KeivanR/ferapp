"""Tests de history.py (page « Semaine »)."""

import datetime
from pathlib import Path

import pytest

from history import average_rates, day_rates, rates_by_day, week_days, week_start
from nutrition import ALL_KEYS, load_foods

FOODS = load_foods(Path(__file__).parent / "foods_demo.csv")
RECOMMENDED = {k: 1000.0 for k in ALL_KEYS} | {"fer": 10.0}
MONDAY = datetime.date(2026, 9, 21)


def test_week_starts_on_monday_and_has_seven_days():
    assert week_start(datetime.date(2026, 9, 27)) == MONDAY  # dimanche -> lundi précédent
    assert week_start(MONDAY) == MONDAY
    days = week_days(MONDAY)
    assert len(days) == 7 and days[0] == MONDAY and days[-1] == datetime.date(2026, 9, 27)


def test_day_rates_none_when_nothing_noted():
    assert day_rates({}, MONDAY, FOODS, RECOMMENDED) is None
    assert day_rates({MONDAY.isoformat(): []}, MONDAY, FOODS, RECOMMENDED) is None


def test_day_rates_are_share_of_recommendation():
    journal = {MONDAY.isoformat(): [{"food": "lentilles cuites", "grams": 200}]}  # 3,3 mg de fer / 100 g
    rates = day_rates(journal, MONDAY, FOODS, RECOMMENDED)
    assert rates["fer"] == pytest.approx(6.6 / 10)


def test_average_ignores_days_without_entries():
    tuesday = MONDAY + datetime.timedelta(days=1)
    journal = {
        MONDAY.isoformat(): [{"food": "lentilles cuites", "grams": 100}],  # fer 3,3 mg -> 33 %
        tuesday.isoformat(): [{"food": "lentilles cuites", "grams": 300}],  # fer 9,9 mg -> 99 %
    }
    rates = rates_by_day(journal, week_days(MONDAY), FOODS, RECOMMENDED)
    assert list(rates) == week_days(MONDAY)
    assert sum(r is not None for r in rates.values()) == 2
    averages = average_rates(rates, ["fer", "calcium"])
    assert averages["fer"] == pytest.approx((0.33 + 0.99) / 2)


def test_average_is_none_for_an_empty_week():
    rates = rates_by_day({}, week_days(MONDAY), FOODS, RECOMMENDED)
    assert average_rates(rates, ["fer"]) == {"fer": None}


def test_browsable_weeks_from_first_noted_week_to_current():
    from history import browsable_weeks

    today = datetime.date(2026, 9, 29)  # mardi
    journal = {"2026-09-02": [{"food": "pomme", "grams": 100}], "2026-09-10": [], "2026-10-05": [{"x": 1}]}
    weeks = browsable_weeks(journal, today)
    assert weeks[0] == datetime.date(2026, 8, 31) and weeks[-1] == datetime.date(2026, 9, 28)
    assert all((b - a).days == 7 for a, b in zip(weeks, weeks[1:]))
    assert browsable_weeks({}, today) == [datetime.date(2026, 9, 28)]  # rien noté : la semaine en cours
    assert len(browsable_weeks({}, today, min_weeks=4)) == 4
