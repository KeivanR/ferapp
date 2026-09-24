"""Logique métier de l'application (aucune dépendance à Flet, donc testable seule).

- base d'aliments chargée depuis foods.csv (valeurs pour 100 g)
- unité familière par défaut de chaque aliment, lue dans config/unites_par_defaut.csv
- apports de référence par nutriment selon le profil (âge, sexe, situation de la femme : règles, grossesse, allaitement),
  lus dans config.toml
- calcul des apports du jour et du taux de complétion

IMPORTANT : les valeurs de référence de config.toml sont des ordres de grandeur inspirés
des références EFSA / ANSES pour un premier prototype. Vérifie-les avant tout usage
réel et ne les utilise pas comme avis médical.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from config import SCALAR_KEYS, load_config, load_default_units

# --------------------------------------------------------------------------- #
# Nutriments et apports de référence : tout vient de config.toml
# --------------------------------------------------------------------------- #
CONFIG = load_config()
NUTRIENTS: list[dict] = CONFIG["nutrients"]  # {"key", "label", "unit", "group", "col", "ciqual"}
REFERENCES: dict[str, dict] = CONFIG["references"]  # par nutriment : homme, femme, femme_regles, femme_regles_abondantes, grossesse, allaitement
SEARCH_LIMIT: int = CONFIG["app"]["suggestions_max"]
AGE_MIN: int = CONFIG["profile"]["age_min"]
AGE_MAX: int = CONFIG["profile"]["age_max"]
PERIOD_AGE_RANGE: tuple[int, int] = tuple(CONFIG["profile"]["menstruation_age_range"])

ALL_KEYS = [n["key"] for n in NUTRIENTS]


# Situations possibles pour une femme (une seule à la fois). Pour chacune : le libellé affiché et
# la liste des clés de référence de config.toml, essayées dans l'ordre (la première définie pour
# le nutriment est utilisée ; « femme » existe toujours, c'est le repli).
WOMAN_STATUSES: dict[str, dict] = {
    "non_reglee": {"label": "Non réglée", "refs": ("femme",)},
    "reglee": {"label": "Réglée", "refs": ("femme_regles", "femme")},
    "abondante": {
        "label": "Abondamment réglée",
        "refs": ("femme_regles_abondantes", "femme_regles", "femme"),
    },
    "enceinte": {"label": "Enceinte", "refs": ("grossesse", "femme")},
    "allaitement": {"label": "Allaitement", "refs": ("allaitement", "femme")},
}


@dataclass
class Profile:
    age: int = CONFIG["profile"]["default_age"]
    sex: str = "F"  # "F" ou "H"
    # Situation d'une femme (clé de WOMAN_STATUSES). None = pas renseignée : on déduit de l'âge
    # (« réglée » dans menstruation_age_range, sinon « non réglée »). Ignoré pour un homme.
    status: str | None = None
    # Clés des nutriments affichés (choix multiple du profil). Par défaut : tous.
    nutrients: list[str] = field(default_factory=lambda: list(ALL_KEYS))

    def effective_status(self) -> str | None:
        """Situation utilisée pour les calculs : None pour un homme."""
        if self.sex != "F":
            return None
        if self.status in WOMAN_STATUSES:
            return self.status
        return "reglee" if PERIOD_AGE_RANGE[0] <= self.age <= PERIOD_AGE_RANGE[1] else "non_reglee"

    def to_dict(self) -> dict:
        return {
            "age": self.age,
            "sex": self.sex,
            "status": self.status,
            "nutrients": list(self.nutrients),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Profile":
        # Un ancien profil sans "nutrients" (ou avec des clés inconnues) retombe sur « tous ».
        chosen = [k for k in d.get("nutrients", []) if k in ALL_KEYS]
        status = d.get("status")
        if status not in WOMAN_STATUSES:
            # Anciens profils (cases séparées) : allaitement > grossesse > règles > estimation.
            if d.get("breastfeeding"):
                status = "allaitement"
            elif d.get("pregnant"):
                status = "enceinte"
            elif d.get("menstruating") is not None:
                status = "reglee" if d["menstruating"] else "non_reglee"
            else:
                status = None
        return cls(
            age=int(d.get("age", CONFIG["profile"]["default_age"])),
            sex=d.get("sex", "F"),
            status=status,
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


def recommended_intakes(
    profile: Profile,
    references: dict[str, dict] | None = None,
    nutrients: list[dict] | None = None,
) -> dict[str, float]:
    """Apport de référence journalier pour chaque nutriment, selon le profil.

    Pour une femme, la clé de référence dépend de sa situation (WOMAN_STATUSES) : on prend la
    première définie pour le nutriment, « femme » en dernier recours.
    `references` / `nutrients` : pour tester avec une autre configuration.
    """
    references = REFERENCES if references is None else references
    nutrients = NUTRIENTS if nutrients is None else nutrients
    out: dict[str, float] = {}
    for n in nutrients:
        ref = references[n["key"]]
        if profile.sex == "H":
            value = _band_value(ref["homme"], profile.age)
        else:
            key = next(k for k in WOMAN_STATUSES[profile.effective_status()]["refs"] if k in ref)
            value = ref[key] if key in SCALAR_KEYS else _band_value(ref[key], profile.age)
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
    """Charge le CSV. Retourne {nom_normalisé: {"name", "code", "per100": {clé: valeur}, "custom": False}}.

    "code" = alim_code Ciqual (None si le CSV n'a pas cette colonne, ex. foods_demo.csv) : c'est
    lui qui relie l'aliment à son unité par défaut (voir default_unit_for).
    """
    foods: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = row["aliment"].strip()
            per100 = {}
            for n in NUTRIENTS:
                raw = (row.get(n["col"]) or "").strip().replace(",", ".")
                per100[n["key"]] = float(raw) if raw else 0.0
            code = (row.get("alim_code") or "").strip() or None
            foods[normalize(name)] = {"name": name, "code": code, "per100": per100, "custom": False}
    return foods


def search_foods(query: str, foods: dict[str, dict], limit: int = SEARCH_LIMIT) -> list[str]:
    """Noms d'aliments correspondant à la saisie : début de nom d'abord, puis « contient
    tous les mots ». Dans chaque groupe : tes aliments personnalisés passent en premier, puis
    le ou les « (aliment moyen) » correspondants (la valeur Ciqual la plus représentative,
    ex. « Pain (aliment moyen) » pour la recherche « pain »), puis les noms les plus courts
    (les plus génériques)."""
    q = normalize(query)
    if not q:
        return []
    starts, contains = [], []
    for norm, food in foods.items():
        if norm.startswith(q):
            starts.append(food)
        elif all(word in norm for word in q.split()):
            contains.append(food)

    def rank(food: dict):
        return (
            not food.get("custom"),
            "(aliment moyen)" not in normalize(food["name"]),
            len(food["name"]),
            food["name"],
        )

    return [f["name"] for f in sorted(starts, key=rank) + sorted(contains, key=rank)][:limit]


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
    """'150', '150 g', '150,5' -> float. None si invalide ou <= 0.

    Sert aussi à parser un nombre d'unités (ex. « 2 fruits ») : même règle (positif, virgule
    ou point), voir ui/widgets.QuantityInput.
    """
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


def top_nutrient(
    entry: dict,
    foods: dict[str, dict],
    recommended: dict[str, float],
    nutrients: list[dict],
) -> dict | None:
    """Nutriment (parmi `nutrients`) que cette entrée apporte le plus.

    Les quantités brutes ne sont pas comparables entre elles (mg, µg, et le potassium
    gagnerait toujours) : on compare donc la part de l'apport journalier recommandé.
    Retourne {"key", "label", "unit", "amount", "share"} ou None si aucune donnée.
    """
    amounts = entry_nutrients(entry, foods)
    best = None
    for n in nutrients:
        amount, rec = amounts[n["key"]], recommended[n["key"]]
        if amount <= 0 or not rec:
            continue
        share = amount / rec
        if best is None or share > best["share"]:
            best = {"key": n["key"], "label": n["label"], "unit": n["unit"], "amount": amount, "share": share}
    return best


def daily_totals(entries: list[dict], foods: dict[str, dict]) -> dict[str, float]:
    totals = {n["key"]: 0.0 for n in NUTRIENTS}
    for e in entries:
        for k, v in entry_nutrients(e, foods).items():
            totals[k] += v
    return totals


def completion(totals: dict[str, float], recommended: dict[str, float]) -> dict[str, float]:
    """Ratio apport / recommandé (peut dépasser 1.0 ; l'affichage plafonne le cercle à 100 %)."""
    return {k: (totals[k] / recommended[k] if recommended[k] else 0.0) for k in totals}


# --------------------------------------------------------------------------- #
# Aliments personnalisés (saisie manuelle ou recette)
# --------------------------------------------------------------------------- #
def parse_nutrient_value(text: str) -> float | None:
    """Teneur saisie à la main : '' -> 0.0, '3,5' -> 3.5, None si invalide ou négative."""
    cleaned = text.strip().replace(",", ".")
    if not cleaned:
        return 0.0
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value >= 0 else None


def recipe_per100(
    ingredients: list[dict], foods: dict[str, dict], final_weight: float | None = None
) -> dict[str, float]:
    """Teneurs pour 100 g d'une recette {"food": nom, "grams": g}, tous nutriments confondus.

    `final_weight` : poids du plat fini (ex. après cuisson) ; par défaut, somme des ingrédients.
    """
    if not ingredients:
        raise ValueError("La recette doit contenir au moins un ingrédient")
    for ing in ingredients:
        if normalize(ing["food"]) not in foods:
            raise ValueError(f"Ingrédient inconnu : {ing['food']}")
    weight = final_weight or sum(i["grams"] for i in ingredients)
    if weight <= 0:
        raise ValueError("Le poids final doit être positif")
    totals = daily_totals(ingredients, foods)
    return {k: v / weight * 100.0 for k, v in totals.items()}


def merge_foods(official: dict[str, dict], custom_foods: list[dict]) -> dict[str, dict]:
    """Base officielle + aliments personnalisés (repérés par "custom": True).

    Un aliment personnalisé enregistré : {"name", "per100", "kind": "manual" | "recipe", ...}.
    """
    merged = dict(official)
    for cf in custom_foods:
        merged[normalize(cf["name"])] = {
            "name": cf["name"],
            "per100": {k: float(cf["per100"].get(k, 0.0)) for k in ALL_KEYS},
            "custom": True,
        }
    return merged


# --------------------------------------------------------------------------- #
# Unités familières (ex. « 1 fruit » = 150 g). Deux sources :
#  - l'unité par défaut de chaque aliment Ciqual, estimée une fois pour toutes dans
#    config/unites_par_defaut.csv (ordres de grandeur, corrigeables dans ce fichier) ;
#  - celles que l'utilisateur définit lui-même pour un aliment (« + Nouvelle unité »),
#    enregistrées dans son état (food_units).
# La quantité saisie avec une unité est convertie en grammes avant d'être stockée dans le
# journal : ce sont donc les seules fonctions du fichier à connaître les unités, le reste
# (calculs, totaux...) continue de raisonner uniquement en grammes.
# --------------------------------------------------------------------------- #
DEFAULT_UNITS: dict[str, dict | None] = load_default_units()  # {alim_code: {"label", "grams"} ou None}


def default_unit_for(
    food_name: str, foods: dict[str, dict], default_units: dict[str, dict | None] | None = None
) -> dict | None:
    """Unité par défaut de cet aliment ({"label", "grams"}, copie), d'après son alim_code dans
    config/unites_par_defaut.csv. None si l'aliment est inconnu, n'a pas de code (aliment
    personnalisé), est absent du fichier ou y est volontairement sans unité.
    `default_units` : pour tester avec un autre fichier (défaut : DEFAULT_UNITS)."""
    default_units = DEFAULT_UNITS if default_units is None else default_units
    food = find_food(food_name, foods)
    if food is None or not food.get("code"):
        return None
    unit = default_units.get(food["code"])
    return dict(unit) if unit else None


def units_for_food(
    food_name: str,
    foods: dict[str, dict],
    food_units: dict[str, list[dict]],
    default_units: dict[str, dict | None] | None = None,
) -> list[dict]:
    """Unités familières proposées pour cet aliment : [{"label": "fruit", "grams": 150}, ...] —
    son unité par défaut (default_unit_for), le cas échéant, suivie de celles que l'utilisateur
    a définies. Si l'utilisateur en a défini une avec le même nom que l'unité par défaut (par ex.
    pour corriger son poids), sa valeur remplace celle par défaut dans la liste.

    Liste vide si l'aliment est inconnu ou n'a aucune unité ; la saisie reste alors possible en
    grammes, toujours disponible (voir ui/widgets.QuantityInput).
    """
    food = find_food(food_name, foods)
    if food is None:
        return []
    units: list[dict] = []
    seen: set[str] = set()
    default = default_unit_for(food_name, foods, default_units)
    if default is not None:
        units.append(default)
        seen.add(normalize(default["label"]))
    for u in food_units.get(normalize(food["name"]), []):
        key = normalize(u["label"])
        if key in seen:
            units = [u if normalize(x["label"]) == key else x for x in units]
        else:
            units.append(u)
            seen.add(key)
    return units


def add_food_unit(
    food_name: str,
    label: str,
    grams: float,
    foods: dict[str, dict],
    food_units: dict[str, list[dict]],
) -> dict:
    """Ajoute une unité familière (ex. "fruit" = 150 g) pour cet aliment et la retourne.

    Lève ValueError (message directement affichable) si l'aliment est inconnu, le nom
    d'unité est vide, réservé ("grammes", l'unité de base toujours disponible) ou déjà pris
    pour cet aliment, ou si les grammes ne sont pas strictement positifs.
    """
    food = find_food(food_name, foods)
    if food is None:
        raise ValueError("Aliment inconnu")
    label = " ".join(label.split())
    if not label:
        raise ValueError("Donne un nom à l'unité")
    if normalize(label) == "grammes":
        raise ValueError("« grammes » est réservé, choisis un autre nom")
    if grams <= 0:
        raise ValueError("Le nombre de grammes doit être positif")
    key = normalize(food["name"])
    existing = food_units.setdefault(key, [])
    if any(normalize(u["label"]) == normalize(label) for u in existing):
        raise ValueError("Cette unité existe déjà pour cet aliment")
    unit = {"label": label, "grams": grams}
    existing.append(unit)
    return unit
