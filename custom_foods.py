"""Aliments personnalisés déjà créés : les retrouver, voir où ils servent, les modifier (y compris
les renommer) et les supprimer. La création elle-même est dans nutrition.py (recipe_per100,
merge_foods) et ui/custom_food.py.

Logique pure, sans Flet, testée dans tests/test_custom_foods.py. Les fonctions qui modifient
prennent l'état complet de storage.load_state, car un aliment perso est cité à plusieurs
endroits : le journal, les recettes d'autres aliments perso, ses unités (food_units) et sa
dernière unité utilisée (last_units).
  - un renommage est répercuté partout ;
  - un changement de teneurs est répercuté sur les recettes qui l'utilisent (recalculées) ;
  - une suppression retire aussi ses repas du journal, et elle est refusée tant qu'une recette
    l'utilise (sinon la recette perdrait une partie de ses nutriments sans prévenir).
"""

from __future__ import annotations

import journal
from nutrition import merge_foods, normalize, recipe_per100


def find_custom(custom_foods: list[dict], name: str) -> dict | None:
    """L'aliment perso de ce nom (casse et accents ignorés), ou None."""
    key = normalize(name)
    return next((f for f in custom_foods if normalize(f["name"]) == key), None)


def recipes_using(custom_foods: list[dict], name: str) -> list[str]:
    """Noms des recettes qui ont cet aliment parmi leurs ingrédients (directement)."""
    key = normalize(name)
    return [
        f["name"]
        for f in custom_foods
        if f.get("kind") == "recipe" and any(normalize(i["food"]) == key for i in f.get("ingredients", []))
    ]


def depends_on(custom_foods: list[dict], food: str, target: str) -> bool:
    """True si `food` est `target`, ou une recette qui contient `target` (même indirectement, via
    une autre recette). Sert à refuser une recette qui se contiendrait elle-même."""
    by_name = {normalize(f["name"]): f for f in custom_foods}
    target_key, seen = normalize(target), set()

    def visit(key: str) -> bool:
        if key == target_key:
            return True
        if key in seen:
            return False
        seen.add(key)
        recipe = by_name.get(key)
        if recipe is None or recipe.get("kind") != "recipe":
            return False
        return any(visit(normalize(i["food"])) for i in recipe.get("ingredients", []))

    return visit(normalize(food))


def food_usage(state: dict, name: str) -> dict:
    """Où sert cet aliment : {"meals": nombre d'entrées du journal, "recipes": [noms de recettes]}."""
    return {"meals": journal.count_food(state["journal"], name), "recipes": recipes_using(state["custom_foods"], name)}


def refresh_recipes(custom_foods: list[dict], official_foods: dict[str, dict]) -> None:
    """Recalcule les teneurs (per100) de toutes les recettes, chaque ingrédient avant la recette
    qui l'utilise. Une recette impossible à recalculer (ingrédient introuvable) garde ses teneurs."""
    foods = merge_foods(official_foods, custom_foods)
    by_name = {normalize(f["name"]): f for f in custom_foods}
    done: set[str] = set()

    def compute(food: dict) -> None:
        key = normalize(food["name"])
        if key in done:
            return
        done.add(key)  # avant les ingrédients : une boucle (données abîmées) ne tourne pas sans fin
        if food.get("kind") != "recipe":
            return
        for ing in food.get("ingredients", []):
            if normalize(ing["food"]) in by_name:
                compute(by_name[normalize(ing["food"])])
        try:
            food["per100"] = recipe_per100(food["ingredients"], foods, food.get("final_weight"))
        except ValueError:
            return
        foods[key]["per100"] = dict(food["per100"])  # les recettes suivantes voient la nouvelle valeur

    for food in custom_foods:
        compute(food)


def update_custom_food(state: dict, old_name: str, food: dict, official_foods: dict[str, dict]) -> None:
    """Remplace l'aliment perso `old_name` par `food` (même format qu'à la création : "name",
    "kind", "per100", et pour une recette "ingredients" et "final_weight").

    Lève ValueError (message affichable) si `old_name` n'existe pas, si le nouveau nom est déjà pris
    par un autre aliment, ou si la recette se contiendrait elle-même."""
    custom_foods = state["custom_foods"]
    current = find_custom(custom_foods, old_name)
    if current is None:
        raise ValueError(f"Aliment introuvable : {old_name}")
    old_key, new_key = normalize(current["name"]), normalize(food["name"])
    if new_key != old_key and (new_key in official_foods or find_custom(custom_foods, food["name"])):
        raise ValueError("Un aliment porte déjà ce nom")
    if food.get("kind") == "recipe":
        for ing in food.get("ingredients", []):
            if depends_on(custom_foods, ing["food"], current["name"]):
                raise ValueError(f"« {ing['food']} » contient déjà cet aliment : une recette ne peut pas se contenir")

    custom_foods[custom_foods.index(current)] = food
    if food["name"] != current["name"]:
        _rename_references(state, current["name"], food["name"])
    refresh_recipes(custom_foods, official_foods)


def _rename_references(state: dict, old: str, new: str) -> None:
    """Répercute un renommage : journal, ingrédients des recettes, unités, dernière unité utilisée."""
    journal.rename_food(state["journal"], old, new)
    old_key, new_key = normalize(old), normalize(new)
    for recipe in state["custom_foods"]:
        for ing in recipe.get("ingredients", []):
            if normalize(ing["food"]) == old_key:
                ing["food"] = new
    for table in ("food_units", "last_units"):
        if old_key in state[table] and old_key != new_key:
            state[table][new_key] = state[table].pop(old_key)


def delete_custom_food(state: dict, name: str) -> None:
    """Supprime l'aliment perso `name`, ses repas du journal, ses unités et sa dernière unité.

    Lève ValueError (message affichable) s'il n'existe pas ou si une recette l'utilise encore."""
    current = find_custom(state["custom_foods"], name)
    if current is None:
        raise ValueError(f"Aliment introuvable : {name}")
    users = recipes_using(state["custom_foods"], name)
    if users:
        listed = ", ".join(f"« {u} »" for u in users)
        raise ValueError(f"Utilisé dans {listed} : retire-le d'abord de cette recette")
    state["custom_foods"].remove(current)
    journal.remove_food(state["journal"], current["name"])
    key = normalize(current["name"])
    state["food_units"].pop(key, None)
    state["last_units"].pop(key, None)
