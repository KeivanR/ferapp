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
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Nutriments suivis : clé (= nom de colonne du CSV sans l'unité), libellé, unité
# --------------------------------------------------------------------------- #
NUTRIENTS = [
    {"key": "fer", "label": "Fer", "unit": "mg", "col": "fer_mg", "group": "Minéraux"},
    {"key": "calcium", "label": "Calcium", "unit": "mg", "col": "calcium_mg", "group": "Minéraux"},
    {"key": "magnesium", "label": "Magnésium", "unit": "mg", "col": "magnesium_mg", "group": "Minéraux"},
    {"key": "zinc", "label": "Zinc", "unit": "mg", "col": "zinc_mg", "group": "Minéraux"},
    {"key": "potassium", "label": "Potassium", "unit": "mg", "col": "potassium_mg", "group": "Minéraux"},
    {"key": "iode", "label": "Iode", "unit": "µg", "col": "iode_ug", "group": "Minéraux"},
    {"key": "selenium", "label": "Sélénium", "unit": "µg", "col": "selenium_ug", "group": "Minéraux"},
    {"key": "vitamine_a", "label": "Vitamine A", "unit": "µg", "col": "vitamine_a_ug", "group": "Vitamines"},
    {"key": "vitamine_d", "label": "Vitamine D", "unit": "µg", "col": "vitamine_d_ug", "group": "Vitamines"},
    {"key": "vitamine_e", "label": "Vitamine E", "unit": "mg", "col": "vitamine_e_mg", "group": "Vitamines"},
    {"key": "vitamine_k", "label": "Vitamine K", "unit": "µg", "col": "vitamine_k1_ug", "group": "Vitamines"},
    {"key": "vitamine_c", "label": "Vitamine C", "unit": "mg", "col": "vitamine_c_mg", "group": "Vitamines"},
    {"key": "vitamine_b9", "label": "Vitamine B9", "unit": "µg", "col": "vitamine_b9_ug", "group": "Vitamines"},
    {"key": "vitamine_b12", "label": "Vitamine B12", "unit": "µg", "col": "vitamine_b12_ug", "group": "Vitamines"},
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
    # --- Vitamines (ordres de grandeur inspirés des références EFSA) ---
    "vitamine_a": {  # µg d'équivalents rétinol
        "H": [(3, 250), (6, 300), (10, 400), (14, 600), (200, 750)],
        "F": [(3, 250), (6, 300), (10, 400), (14, 600), (200, 650)],
        "grossesse": 700,
        "allaitement": 1300,
    },
    "vitamine_d": {  # µg, apport adéquat identique pour tous à partir de 1 an
        **_BOTH([(200, 15)]),
    },
    "vitamine_e": {  # mg d'alpha-tocophérol
        "H": [(3, 6), (10, 9), (14, 13), (200, 13)],
        "F": [(3, 6), (10, 9), (14, 11), (200, 11)],
    },
    "vitamine_k": {  # µg (K1)
        **_BOTH([(3, 12), (6, 20), (10, 30), (14, 45), (17, 65), (200, 70)]),
    },
    "vitamine_c": {  # mg
        "H": [(3, 20), (6, 30), (10, 45), (14, 70), (17, 100), (200, 110)],
        "F": [(3, 20), (6, 30), (10, 45), (14, 70), (17, 90), (200, 95)],
        "grossesse": 105,
        "allaitement": 155,
    },
    "vitamine_b9": {  # µg (folates)
        **_BOTH([(3, 120), (6, 140), (10, 200), (14, 270), (200, 330)]),
        "grossesse": 600,
        "allaitement": 500,
    },
    "vitamine_b12": {  # µg
        **_BOTH([(6, 1.5), (10, 2.5), (14, 3.5), (200, 4)]),
        "grossesse": 4.5,
        "allaitement": 5,
    },
}


ALL_KEYS = [n["key"] for n in NUTRIENTS]


@dataclass
class Profile:
    age: int = 30
    sex: str = "F"  # "F" ou "H"
    pregnant: bool = False
    breastfeeding: bool = False
    # Clés des nutriments affichés (choix multiple du profil). Par défaut : tous.
    nutrients: list[str] = field(default_factory=lambda: list(ALL_KEYS))

    def to_dict(self) -> dict:
        return {
            "age": self.age,
            "sex": self.sex,
            "pregnant": self.pregnant,
            "breastfeeding": self.breastfeeding,
            "nutrients": list(self.nutrients),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        # Un ancien profil sans "nutrients" (ou avec des clés inconnues) retombe sur « tous ».
        chosen = [k for k in d.get("nutrients", []) if k in ALL_KEYS]
        return cls(
            age=int(d.get("age", 30)),
            sex=d.get("sex", "F"),
            pregnant=bool(d.get("pregnant", False)),
            breastfeeding=bool(d.get("breastfeeding", False)),
            nutrients=chosen or list(ALL_KEYS),
        )


def selected_nutrients(profile: Profile) -> list[dict]:
    """Nutriments choisis par l'utilisateur, dans l'ordre de NUTRIENTS."""
    return [n for n in NUTRIENTS if n["key"] in profile.nutrients]


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


def search_foods(query: str, foods: dict[str, dict], limit: int = 8) -> list[str]:
    """Noms d'aliments correspondant à la saisie : début de nom d'abord, puis « contient
    tous les mots » ; dans chaque groupe, les noms les plus courts (les plus génériques) en premier."""
    q = normalize(query)
    if not q:
        return []
    starts, contains = [], []
    for norm, food in foods.items():
        if norm.startswith(q):
            starts.append(food["name"])
        elif all(word in norm for word in q.split()):
            contains.append(food["name"])
    return (sorted(starts, key=lambda s: (len(s), s)) + sorted(contains, key=lambda s: (len(s), s)))[:limit]


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