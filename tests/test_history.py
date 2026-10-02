"""Tests de history.py (page « Semaine »)."""

import datetime
from pathlib import Path

import pytest

from history import average_totals, day_totals, totals_by_day, week_days, week_start, week_summary
from nutrition import load_foods

FOODS = load_foods(Path(__file__).parent / "foods_demo.csv")
MONDAY = datetime.date(2026, 9, 21)


def test_week_starts_on_monday_and_has_seven_days():
    assert week_start(datetime.date(2026, 9, 27)) == MONDAY  # dimanche -> lundi précédent
    assert week_start(MONDAY) == MONDAY
    days = week_days(MONDAY)
    assert len(days) == 7 and days[0] == MONDAY and days[-1] == datetime.date(2026, 9, 27)


def test_day_totals_none_when_nothing_noted():
    assert day_totals({}, MONDAY, FOODS) is None
    assert day_totals({MONDAY.isoformat(): []}, MONDAY, FOODS) is None


def test_day_totals_are_amounts():
    journal = {MONDAY.isoformat(): [{"food": "lentilles cuites", "grams": 200}]}  # 3,3 mg de fer / 100 g
    assert day_totals(journal, MONDAY, FOODS)["fer"] == pytest.approx(6.6)


def test_average_ignores_days_without_entries():
    tuesday = MONDAY + datetime.timedelta(days=1)
    journal = {
        MONDAY.isoformat(): [{"food": "lentilles cuites", "grams": 100}],  # fer 3,3 mg
        tuesday.isoformat(): [{"food": "lentilles cuites", "grams": 300}],  # fer 9,9 mg
    }
    totals = totals_by_day(journal, week_days(MONDAY), FOODS)
    assert list(totals) == week_days(MONDAY)
    assert sum(t is not None for t in totals.values()) == 2
    averages = average_totals(totals, ["fer", "calcium"])
    assert averages["fer"] == pytest.approx((3.3 + 9.9) / 2)


def test_average_is_none_for_an_empty_week():
    totals = totals_by_day({}, week_days(MONDAY), FOODS)
    assert average_totals(totals, ["fer"]) == {"fer": None}


def test_browsable_weeks_from_first_noted_week_to_current():
    from history import browsable_weeks

    today = datetime.date(2026, 9, 29)  # mardi
    journal = {"2026-09-02": [{"food": "pomme", "grams": 100}], "2026-09-10": [], "2026-10-05": [{"x": 1}]}
    weeks = browsable_weeks(journal, today)
    assert weeks[0] == datetime.date(2026, 8, 31) and weeks[-1] == datetime.date(2026, 9, 28)
    assert all((b - a).days == 7 for a, b in zip(weeks, weeks[1:]))
    assert browsable_weeks({}, today) == [datetime.date(2026, 9, 28)]  # rien noté : la semaine en cours
    assert len(browsable_weeks({}, today, min_weeks=4)) == 4


def test_week_summary_gathers_totals_averages_and_filled_days():
    journal = {MONDAY.isoformat(): [{"food": "lentilles cuites", "grams": 100}]}  # fer 3,3 mg
    summary = week_summary(journal, MONDAY, FOODS, ["fer"])
    assert summary.days == week_days(MONDAY)
    assert summary.filled_days == 1
    assert summary.totals[MONDAY]["fer"] == pytest.approx(3.3)
    assert summary.totals[MONDAY + datetime.timedelta(days=1)] is None
    assert summary.averages == {"fer": pytest.approx(3.3)}
