"""Suivi sur plusieurs jours (page « Semaine ») : apports jour par jour et moyennes.

Logique pure, sans Flet, testée dans tests/test_history.py. Le journal est celui de
storage.load_state : {"AAAA-MM-JJ": [{"food": nom, "grams": g}, ...]}.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from nutrition import daily_totals

DAYS_PER_WEEK = 7


def week_start(day: datetime.date) -> datetime.date:
    """Lundi de la semaine qui contient `day`."""
    return day - datetime.timedelta(days=day.weekday())


def week_days(start: datetime.date) -> list[datetime.date]:
    """Les 7 jours de la semaine qui commence le lundi `start`."""
    return [start + datetime.timedelta(days=i) for i in range(DAYS_PER_WEEK)]


def day_totals(journal: dict[str, list[dict]], day: datetime.date, foods: dict[str, dict]) -> dict[str, float] | None:
    """Quantité de chaque nutriment apportée ce jour-là, ou None si rien n'a été noté (à distinguer
    d'une journée réellement à zéro)."""
    entries = journal.get(day.isoformat()) or []
    if not entries:
        return None
    return daily_totals(entries, foods)


def totals_by_day(
    journal: dict[str, list[dict]], days: list[datetime.date], foods: dict[str, dict]
) -> dict[datetime.date, dict[str, float] | None]:
    """day_totals pour chacun des `days`, dans l'ordre."""
    return {day: day_totals(journal, day, foods) for day in days}


def average_totals(totals: dict[datetime.date, dict[str, float] | None], keys: list[str]) -> dict[str, float | None]:
    """Quantité moyenne par jour de chaque nutriment de `keys`, calculée uniquement sur les jours
    où quelque chose a été noté (un jour oublié ne fait pas baisser la moyenne) ; None si aucun
    jour n'en a."""
    filled = [t for t in totals.values() if t is not None]
    return {k: (sum(t[k] for t in filled) / len(filled) if filled else None) for k in keys}


@dataclass
class WeekSummary:
    """Tout ce qu'affiche une semaine de la page « Semaine ». Les valeurs sont des quantités (mg,
    g...) : c'est l'écran qui les compare au repère de chaque nutriment (nutrition.intake_status),
    car certains nutriments sont à atteindre, d'autres à limiter, d'autres n'ont pas de repère."""

    days: list[datetime.date]  # du lundi au dimanche
    totals: dict[datetime.date, dict[str, float] | None]  # day_totals de chaque jour
    averages: dict[str, float | None]  # average_totals de la semaine
    filled_days: int  # jours où quelque chose a été noté


def week_summary(
    journal: dict[str, list[dict]], start: datetime.date, foods: dict[str, dict], keys: list[str]
) -> WeekSummary:
    """Quantités jour par jour, moyennes (nutriments de `keys`) et nombre de jours notés de la
    semaine qui commence le lundi `start`."""
    days = week_days(start)
    totals = totals_by_day(journal, days, foods)
    return WeekSummary(
        days=days,
        totals=totals,
        averages=average_totals(totals, keys),
        filled_days=sum(t is not None for t in totals.values()),
    )


def browsable_weeks(journal: dict[str, list[dict]], today: datetime.date, min_weeks: int = 1) -> list[datetime.date]:
    """Lundis des semaines consultables, de la plus ancienne à la semaine en cours : depuis la première
    semaine où quelque chose a été noté, et au moins `min_weeks` semaines."""
    current = week_start(today)
    noted = [datetime.date.fromisoformat(day) for day, entries in journal.items() if entries]
    first = min([week_start(d) for d in noted if d <= today], default=current)
    first = min(first, current - datetime.timedelta(weeks=min_weeks - 1))
    count = (current - first).days // DAYS_PER_WEEK + 1
    return [first + datetime.timedelta(weeks=i) for i in range(count)]
