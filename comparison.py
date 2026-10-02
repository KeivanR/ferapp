"""Comparer des aliments entre eux (onglet « Comparer ») : ce qu'une même quantité de chacun
apporte pour chaque nutriment suivi, en part de l'apport journalier recommandé.

Logique pure, sans Flet, testée dans tests/test_comparison.py.

La sélection est une liste [{"name": nom, "slot": n}, ...] dans l'ordre d'ajout. Le `slot`
(0, 1, 2...) désigne la couleur et la lettre (A, B, C...) de l'aliment : il lui est attribué à
l'ajout et ne change plus, pour qu'un aliment garde sa couleur quand on en retire un autre.
"""

from __future__ import annotations

from nutrition import entry_nutrients, normalize, units_for_food

REFERENCE_GRAMS = 100.0  # quantité comparée quand on ne compare pas « par portion »
# Graduations possibles pour le bout de l'axe (en fraction de l'apport recommandé) : on prend la
# plus petite qui contient toutes les barres, pour qu'elles occupent la largeur disponible.
AXIS_STEPS = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0)


def slot_letter(slot: int) -> str:
    """0 -> « A », 1 -> « B »..."""
    return chr(ord("A") + slot)


def valid_selection(selection: list[dict], foods: dict[str, dict]) -> list[dict]:
    """La sélection sans les aliments qui n'existent plus (aliment perso supprimé ou renommé)."""
    return [s for s in selection if normalize(s["name"]) in foods]


def is_selected(selection: list[dict], name: str) -> bool:
    return any(normalize(s["name"]) == normalize(name) for s in selection)


def add_food(selection: list[dict], name: str, max_foods: int) -> bool:
    """Ajoute `name` à la sélection avec le premier slot libre. False (rien n'est ajouté) s'il y
    est déjà ou si la sélection est pleine."""
    if is_selected(selection, name) or len(selection) >= max_foods:
        return False
    used = {s["slot"] for s in selection}
    slot = next(i for i in range(max_foods) if i not in used)
    selection.append({"name": name, "slot": slot})
    return True


def remove_food(selection: list[dict], name: str) -> None:
    selection[:] = [s for s in selection if normalize(s["name"]) != normalize(name)]


def portion_for(name: str, foods: dict[str, dict], food_units: dict[str, list[dict]]) -> dict | None:
    """Portion habituelle de l'aliment : sa première unité familière ({"label", "grams"}, ex. un
    fruit de 150 g), ou None s'il n'en a pas."""
    units = units_for_food(name, foods, food_units)
    return dict(units[0]) if units else None


def compared_grams(name: str, foods: dict[str, dict], food_units: dict[str, list[dict]], per_portion: bool) -> float:
    """Quantité comparée pour cet aliment : sa portion habituelle si `per_portion` (et s'il en a
    une), sinon REFERENCE_GRAMS."""
    portion = portion_for(name, foods, food_units) if per_portion else None
    return portion["grams"] if portion else REFERENCE_GRAMS


def nutrient_shares(
    name: str, grams: float, foods: dict[str, dict], recommended: dict[str, float], keys: list[str]
) -> dict[str, dict]:
    """Pour chaque nutriment de `keys`, ce qu'apportent `grams` g de l'aliment :
    {clé: {"amount": quantité, "ratio": part de l'apport recommandé (1.0 = 100 %)}}."""
    amounts = entry_nutrients({"food": name, "grams": grams}, foods)
    return {
        k: {"amount": amounts[k], "ratio": amounts[k] / recommended[k] if recommended.get(k) else 0.0} for k in keys
    }


def best_slots(shares_by_slot: dict[int, dict[str, dict]], key: str) -> set[int]:
    """Slots des aliments qui apportent le plus du nutriment `key` (plusieurs en cas d'égalité ;
    aucun si personne n'en apporte, ou s'il n'y a qu'un aliment : rien à comparer)."""
    if len(shares_by_slot) < 2:
        return set()
    top = max(shares[key]["amount"] for shares in shares_by_slot.values())
    return {slot for slot, shares in shares_by_slot.items() if top > 0 and shares[key]["amount"] == top}


def axis_max(ratios: list[float], cap: float) -> float:
    """Valeur du bout de l'axe, commune à tout le graphique : la plus petite graduation de
    AXIS_STEPS qui contient le plus grand ratio, sans dépasser `cap`. Une barre au-delà de `cap`
    (ex. un abat très riche en vitamine B12) est dessinée pleine, avec une marque « dépasse » :
    sans cette limite, elle écraserait toutes les autres."""
    top = max(ratios, default=0.0)
    steps = [s for s in AXIS_STEPS if s <= cap] or [cap]
    return next((s for s in steps if s >= top), steps[-1])


def frequent_foods(journal: dict[str, list[dict]], foods: dict[str, dict], limit: int) -> list[str]:
    """Les aliments les plus souvent notés dans le journal (du plus au moins fréquent, puis par
    ordre alphabétique), parmi ceux qui existent encore : des raccourcis pour la comparaison."""
    counts: dict[str, int] = {}
    for entries in journal.values():
        for entry in entries:
            key = normalize(entry["food"])
            if key in foods:
                counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts, key=lambda k: (-counts[k], k))
    return [foods[k]["name"] for k in ranked[:limit]]
