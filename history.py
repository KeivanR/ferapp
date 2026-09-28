"""Suivi sur plusieurs jours (page « Semaine ») : taux de complétion jour par jour et moyennes.

Logique pure, sans Flet, testée dans tests/test_history.py. Le journal est celui de
storage.load_state : {"AAAA-MM-JJ": [{"food": nom, "grams": g}, ...]}.
"""

from __future__ import annotations

import datetime

from nutrition import completion, daily_totals

DAYS_PER_WEEK = 7


def week_start(day: datetime.date) -> datetime.date:
    """Lundi de la semaine qui contient `day`."""
    return day - datetime.timedelta(days=day.weekday())


def week_days(start: datetime.date) -> list[datetime.date]:
    """Les 7 jours de la semaine qui commence le lundi `start`."""
    return [start + datetime.timedelta(days=i) for i in range(DAYS_PER_WEEK)]


def day_rates(
    journal: dict[str, list[dict]],
    day: datetime.date,
    foods: dict[str, dict],
    recommended: dict[str, float],
) -> dict[str, float] | None:
    """Taux de complétion de chaque nutriment ce jour-là (1.0 = apport recommandé atteint),
    ou None si rien n'a été noté ce jour-là (à distinguer d'une journée réellement à 0 %)."""
    entries = journal.get(day.isoformat()) or []
    if not entries:
        return None
    return completion(daily_totals(entries, foods), recommended)


def rates_by_day(
    journal: dict[str, list[dict]],
    days: list[datetime.date],
    foods: dict[str, dict],
    recommended: dict[str, float],
) -> dict[datetime.date, dict[str, float] | None]:
    """day_rates pour chacun des `days`, dans l'ordre."""
    return {day: day_rates(journal, day, foods, recommended) for day in days}


def average_rates(rates: dict[datetime.date, dict[str, float] | None], keys: list[str]) -> dict[str, float | None]:
    """Taux moyen de chaque nutriment de `keys`, calculé uniquement sur les jours où quelque chose
    a été noté (un jour oublié ne fait pas baisser la moyenne) ; None si aucun jour n'en a."""
    filled = [r for r in rates.values() if r is not None]
    return {k: (sum(r[k] for r in filled) / len(filled) if filled else None) for k in keys}
