"""Dates écrites en français, partagées par les écrans (accueil, semaine, détail d'un nutriment).

Aucun import de Flet : testé dans tests/test_dates.py. Changer un libellé ici le change partout.
"""

from __future__ import annotations

import datetime

DAY_LETTERS = ["L", "M", "M", "J", "V", "S", "D"]
DAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip


def picked_date(value: datetime.date | datetime.datetime) -> datetime.date:
    """Jour choisi dans un ft.DatePicker. Le calendrier renvoie minuit, heure du téléphone, convertie
    en UTC : en France, le 23 septembre arrive comme « 22 septembre, 22 h UTC ». On arrondit donc au
    minuit le plus proche, ce qui redonne le bon jour quel que soit le fuseau horaire (de -12 h à +12 h)."""
    if not isinstance(value, datetime.datetime):
        return value
    if value.tzinfo is not None:
        value = value.astimezone(datetime.timezone.utc)
    return (value + datetime.timedelta(hours=12)).date()


def long_date(day: datetime.date) -> str:
    """« mardi 23 septembre »."""
    return f"{DAY_NAMES[day.weekday()]} {day.day} {MONTHS[day.month - 1]}"


def numeric_date(day: datetime.date) -> str:
    """« 23/09/2026 »."""
    return day.strftime("%d/%m/%Y")


def day_label(day: datetime.date, today: datetime.date) -> str:
    """« aujourd'hui », « hier », sinon « mardi 23 septembre » (à placer dans une phrase)."""
    if day == today:
        return "aujourd'hui"
    if day == today - datetime.timedelta(days=1):
        return "hier"
    return long_date(day)


def day_title(day: datetime.date, today: datetime.date) -> str:
    """Titre d'écran : « Aujourd'hui », « Hier », « Mardi 23 septembre »."""
    label = day_label(day, today)
    return label[0].upper() + label[1:]


def meals_title(day: datetime.date, today: datetime.date) -> str:
    """Titre de la liste des repas : « Repas du jour », « Repas d'hier », « Repas du mardi 23 septembre »."""
    if day == today:
        return "Repas du jour"
    if day == today - datetime.timedelta(days=1):
        return "Repas d'hier"
    return f"Repas du {long_date(day)}"


def week_label(start: datetime.date) -> str:
    """« du 21 au 27 septembre 2026 », « du 29 septembre au 5 octobre 2026 »..."""
    end = start + datetime.timedelta(days=6)
    if start.year != end.year:
        return f"du {start.day} {MONTHS[start.month - 1]} {start.year} au {end.day} {MONTHS[end.month - 1]} {end.year}"
    if start.month != end.month:
        return f"du {start.day} {MONTHS[start.month - 1]} au {end.day} {MONTHS[end.month - 1]} {end.year}"
    return f"du {start.day} au {end.day} {MONTHS[end.month - 1]} {end.year}"
