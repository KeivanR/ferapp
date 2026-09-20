"""Logique métier de l'application (aucune dépendance à Flet, donc testable seule).

- base d'aliments chargée depuis foods.csv (valeurs pour 100 g)
- apports de référence par nutriment selon le profil (âge, sexe, grossesse, allaitement)
- calcul des apports du jour et du taux de complétion

IMPORTANT : les valeurs de référence ci-dessous sont des ordres de grandeur inspirés
des références EFSA / ANSES pour un premier prototype. Vérifie-les avant tout usage
réel et ne les utilise pas comme avis médical.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------- #
# Nutriments suivis : clé (= nom de colonne du CSV sans l'unité), libellé, unité
# --------------------------------------------------------------------------- #
NUTRIENTS = [
    {"key": "fer", "label": "Fer", "unit": "mg", "col": "fer_mg"},
    {"key": "calcium", "label": "Calcium", "unit": "mg", "col": "calcium_mg"},
    {"key": "magnesium", "label": "Magnésium", "unit": "mg", "col": "magnesium_mg"},
    {"key": "zinc", "label": "Zinc", "unit": "mg", "col": "zinc_mg"},
    {"key": "potassium", "label": "Potassium", "unit": "mg", "col": "potassium_mg"},
    {"key": "iode", "label": "Iode", "unit": "µg", "col": "iode_ug"},
    {"key": "selenium", "label": "Sélénium", "unit": "µg", "col": "selenium_ug"},
]

# --------------------------------------------------------------------------- #
# Apports de référence. Chaque tranche d'âge est (âge_max_inclus, valeur).
# "H" = homme, "F" = femme. "grossesse" / "allaitement" : valeur unique (adulte),
# à défaut on retombe sur la valeur "F" correspondant à l'âge.
# --------------------------------------------------------------------------- #
_BOTH = lambda bands: {"H": bands, "F": bands}  # noqa: E731

REFERENCES: dict[str, dict] = {
    "fer": {
        "H": [(3, 7), (10, 11), (17, 13), (200, 11)],
        "F": [(3, 7), (10, 11), (17, 16), (50, 16), (200, 11)],
        "grossesse": 16,
        "allaitement": 10,
    },
    "calcium": {
        **_BOTH([(3, 450), (10, 800), (17, 1150), (24, 1000), (200, 950)]),
    },
    "magnesium": {
        "H": [(3, 170), (10, 230), (14, 250), (17, 350), (200, 350)],
        "F": [(3, 170), (10, 230), (14, 250), (17, 300), (200, 300)],
    },
    "zinc": {
        "H": [(3, 4.3), (6, 5.5), (10, 7.4), (14, 10.7), (17, 11.9), (200, 11.0)],
        "F": [(3, 4.3), (6, 5.5), (10, 7.4), (14, 10.7), (17, 10.2), (200, 8.9)],
        "grossesse": 10.5,
        "allaitement": 11.8,
    },
    "potassium": {
        **_BOTH([(3, 800), (6, 1800), (10, 2000), (14, 2900), (17, 3500), (200, 3500)]),
        "allaitement": 4000,
    },
    "iode": {
        **_BOTH([(10, 90), (14, 120), (200, 150)]),
        "grossesse": 200,
        "allaitement": 200,
    },
    "selenium": {
        **_BOTH([(3, 15), (6, 30), (10, 45), (14, 60), (200, 70)]),
        "allaitement": 85,
    },
}


@dataclass
class Profile:
    age: int = 30
    sex: str = "F"  # "F" ou "H"
    pregnant: bool = False
    breastfeeding: bool = False

    def to_dict(self) -> dict:
        return {
            "age": self.age,
            "sex": self.sex,
            "pregnant": self.pregnant,
            "breastfeeding": self.breastfeeding,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        return cls(
            age=int(d.get("age", 30)),
            sex=d.get("sex", "F"),
            pregnant=bool(d.get("pregnant", False)),
            breastfeeding=bool(d.get("breastfeeding", False)),
        )


def _band_value(bands: list[tuple[int, float]], age: int) -> float:
    for max_age, value in bands:
        if age <= max_age:
            return value
    return bands[-1][1]


def recommended_intakes(profile: Profile) -> dict[str, float]:
    """Apport de référence journalier pour chaque nutriment, selon le profil."""
    out: dict[str, float] = {}
    for n in NUTRIENTS:
        ref = REFERENCES[n["key"]]
        value = _band_value(ref[profile.sex], profile.age)
        if profile.sex == "F":
            # Allaitement prioritaire sur grossesse si les deux sont cochés.
            if profile.breastfeeding and "allaitement" in ref:
                value = ref["allaitement"]
            elif profile.pregnant and "grossesse" in ref:
                value = ref["grossesse"]
        out[n["key"]] = value
    return out


# --------------------------------------------------------------------------- #
# Base d'aliments
# --------------------------------------------------------------------------- #
def normalize(text: str) -> str:
    """Minuscule, sans accents, espaces réduits : 'Épinards  Cuits' -> 'epinards cuits'."""
    text = unicodedata.normalize("NFD", text.strip().lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return " ".join(text.split())


def load_foods(path: str | Path) -> dict[str, dict]:
    """Charge le CSV. Retourne {nom_normalisé: {"name": nom, "per100": {clé: valeur}}}."""
    foods: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["aliment"].strip()
            per100 = {}
            for n in NUTRIENTS:
                raw = (row.get(n["col"]) or "").strip().replace(",", ".")
                per100[n["key"]] = float(raw) if raw else 0.0
            foods[normalize(name)] = {"name": name, "per100": per100}
    return foods


def search_foods(query: str, foods: dict[str, dict], limit: int = 6) -> list[str]:
    """Noms d'aliments correspondant à la saisie (début de nom d'abord, puis contient)."""
    q = normalize(query)
    if not q:
        return []
    starts, contains = [], []
    for norm, food in foods.items():
        if norm.startswith(q):
            starts.append(food["name"])
        elif all(word in norm for word in q.split()):
            contains.append(food["name"])
    return (sorted(starts) + sorted(contains))[:limit]


def find_food(name: str, foods: dict[str, dict]) -> dict | None:
    """Correspondance exacte (insensible à la casse/accents), sinon unique résultat de recherche."""
    norm = normalize(name)
    if norm in foods:
        return foods[norm]
    matches = search_foods(name, foods, limit=2)
    if len(matches) == 1:
        return foods[normalize(matches[0])]
    return None


def parse_grams(text: str) -> float | None:
    """'150', '150 g', '150,5' -> float. None si invalide ou <= 0."""
    cleaned = text.strip().lower().replace(",", ".").removesuffix("g").strip()
    try:
        grams = float(cleaned)
    except ValueError:
        return None
    return grams if grams > 0 else None


# --------------------------------------------------------------------------- #
# Calculs
# --------------------------------------------------------------------------- #
def entry_nutrients(entry: dict, foods: dict[str, dict]) -> dict[str, float]:
    """Nutriments apportés par une entrée {"food": nom, "grams": g}."""
    food = foods.get(normalize(entry["food"]))
    if food is None:
        return {n["key"]: 0.0 for n in NUTRIENTS}
    factor = entry["grams"] / 100.0
    return {k: v * factor for k, v in food["per100"].items()}


def daily_totals(entries: list[dict], foods: dict[str, dict]) -> dict[str, float]:
    totals = {n["key"]: 0.0 for n in NUTRIENTS}
    for e in entries:
        for k, v in entry_nutrients(e, foods).items():
            totals[k] += v
    return totals


def completion(totals: dict[str, float], recommended: dict[str, float]) -> dict[str, float]:
    """Ratio apport / recommandé (peut dépasser 1.0 ; l'affichage plafonne le cercle à 100 %)."""
    return {k: (totals[k] / recommended[k] if recommended[k] else 0.0) for k in totals}
