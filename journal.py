"""Journal alimentaire : ce qui a été mangé, jour par jour, et comment le modifier.

Logique pure, sans Flet, testée dans tests/test_journal.py. Le journal est celui de
storage.load_state : {"AAAA-MM-JJ": [{"food": nom, "grams": g}, ...]}. N'importe quel jour
passé se modifie comme aujourd'hui : il suffit de passer sa date.

Un jour sans aucune entrée est retiré du journal : on ne garde pas de listes vides pour
les jours simplement consultés.
"""

from __future__ import annotations

import datetime

from nutrition import normalize


def day_key(day: datetime.date) -> str:
    """Clé d'un jour dans le journal : « 2026-09-23 »."""
    return day.isoformat()


def entries_for(journal: dict[str, list[dict]], day: datetime.date) -> list[dict]:
    """Entrées du jour `day` (liste vide si rien n'a été noté). À lire seulement : pour modifier,
    utiliser add_entry, replace_entry et delete_entry."""
    return journal.get(day_key(day), [])


def add_entry(journal: dict[str, list[dict]], day: datetime.date, food: str, grams: float) -> None:
    """Ajoute `grams` g de `food` à la fin du jour `day`."""
    journal.setdefault(day_key(day), []).append({"food": food, "grams": grams})


def replace_entry(journal: dict[str, list[dict]], day: datetime.date, index: int, food: str, grams: float) -> None:
    """Remplace la `index`-ième entrée du jour `day` (IndexError si elle n'existe pas)."""
    entries = journal.get(day_key(day), [])
    if not 0 <= index < len(entries):
        raise IndexError(f"Pas d'entrée n°{index} le {day_key(day)}")
    entries[index] = {"food": food, "grams": grams}


def delete_entry(journal: dict[str, list[dict]], day: datetime.date, index: int) -> None:
    """Supprime la `index`-ième entrée du jour `day` (rien si elle n'existe pas). Le jour est
    retiré du journal s'il ne contient plus rien."""
    key = day_key(day)
    entries = journal.get(key, [])
    if 0 <= index < len(entries):
        entries.pop(index)
    if key in journal and not journal[key]:
        del journal[key]


# --- Un aliment dans tout le journal (renommer ou supprimer un aliment perso, voir custom_foods.py) ---


def count_food(journal: dict[str, list[dict]], food: str) -> int:
    """Nombre d'entrées du journal, tous jours confondus, pour cet aliment (casse et accents ignorés)."""
    key = normalize(food)
    return sum(normalize(e["food"]) == key for entries in journal.values() for e in entries)


def rename_food(journal: dict[str, list[dict]], old: str, new: str) -> None:
    """Toutes les entrées de `old` deviennent des entrées de `new` (mêmes grammes)."""
    key = normalize(old)
    for entries in journal.values():
        for e in entries:
            if normalize(e["food"]) == key:
                e["food"] = new


def remove_food(journal: dict[str, list[dict]], food: str) -> None:
    """Retire toutes les entrées de cet aliment ; les jours devenus vides sont retirés."""
    key = normalize(food)
    for day in list(journal):
        journal[day] = [e for e in journal[day] if normalize(e["food"]) != key]
        if not journal[day]:
            del journal[day]
