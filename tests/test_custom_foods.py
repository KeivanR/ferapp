"""Tests de custom_foods.py : modifier, renommer et supprimer un aliment perso."""

import copy
from pathlib import Path

import pytest

from custom_foods import (
    delete_custom_food,
    depends_on,
    find_custom,
    food_usage,
    recipes_using,
    update_custom_food,
)
from nutrition import ALL_KEYS, load_foods, merge_foods, normalize, recipe_per100

FOODS = load_foods(Path(__file__).parent / "foods_demo.csv")
BARRE = {"name": "Barre maison", "kind": "manual", "per100": {k: 0.0 for k in ALL_KEYS} | {"fer": 5.0}}


def make_state() -> dict:
    """Un aliment saisi à la main, une recette qui l'utilise, et une recette qui utilise la recette."""
    barre = copy.deepcopy(BARRE)
    bowl_ings = [{"food": "Barre maison", "grams": 50}, {"food": "lentilles cuites", "grams": 50}]
    bowl = {"name": "Bol", "kind": "recipe", "ingredients": bowl_ings, "final_weight": None}
    bowl["per100"] = recipe_per100(bowl_ings, merge_foods(FOODS, [barre]))
    menu_ings = [{"food": "Bol", "grams": 100}]
    menu = {"name": "Menu", "kind": "recipe", "ingredients": menu_ings, "final_weight": None}
    menu["per100"] = recipe_per100(menu_ings, merge_foods(FOODS, [barre, bowl]))
    return {
        "profile": None,
        "journal": {
            "2026-09-23": [{"food": "Barre maison", "grams": 40}, {"food": "baguette", "grams": 50}],
            "2026-09-24": [{"food": "barre maison", "grams": 20}],
        },
        "custom_foods": [barre, bowl, menu],
        "food_units": {"barre maison": [{"label": "barre", "grams": 40}]},
        "last_units": {"barre maison": "barre"},
    }


def test_find_and_usage():
    state = make_state()
    assert find_custom(state["custom_foods"], "BARRE MAISON")["name"] == "Barre maison"
    assert find_custom(state["custom_foods"], "inconnu") is None
    assert recipes_using(state["custom_foods"], "Barre maison") == ["Bol"]
    assert food_usage(state, "Barre maison") == {"meals": 2, "recipes": ["Bol"]}


def test_depends_on_is_transitive():
    foods = make_state()["custom_foods"]
    assert depends_on(foods, "Menu", "Barre maison")
    assert depends_on(foods, "Bol", "Bol")
    assert not depends_on(foods, "Barre maison", "Menu")
    assert not depends_on(foods, "baguette", "Barre maison")


def test_changing_nutrients_updates_recipes_using_it():
    state = make_state()
    new = copy.deepcopy(BARRE)
    new["per100"]["fer"] = 15.0
    update_custom_food(state, "Barre maison", new, FOODS)
    bowl, menu = state["custom_foods"][1], state["custom_foods"][2]
    lentil_iron = FOODS[normalize("lentilles cuites")]["per100"]["fer"]
    assert bowl["per100"]["fer"] == pytest.approx((15.0 * 0.5 + lentil_iron * 0.5) / 100 * 100)
    assert menu["per100"]["fer"] == pytest.approx(bowl["per100"]["fer"])  # 100 g de bol = 100 g de menu


def test_rename_is_applied_everywhere():
    state = make_state()
    new = copy.deepcopy(BARRE) | {"name": "Barre de céréales"}
    update_custom_food(state, "Barre maison", new, FOODS)
    assert [e["food"] for e in state["journal"]["2026-09-23"]] == ["Barre de céréales", "baguette"]
    assert state["journal"]["2026-09-24"][0]["food"] == "Barre de céréales"
    assert state["custom_foods"][1]["ingredients"][0]["food"] == "Barre de céréales"
    assert state["food_units"] == {"barre de cereales": [{"label": "barre", "grams": 40}]}
    assert state["last_units"] == {"barre de cereales": "barre"}


def test_rename_refuses_a_taken_name():
    state = make_state()
    with pytest.raises(ValueError, match="déjà"):
        update_custom_food(state, "Barre maison", copy.deepcopy(BARRE) | {"name": "Baguette"}, FOODS)
    with pytest.raises(ValueError, match="déjà"):
        update_custom_food(state, "Barre maison", copy.deepcopy(BARRE) | {"name": "bol"}, FOODS)
    update_custom_food(state, "Barre maison", copy.deepcopy(BARRE) | {"name": "barre MAISON"}, FOODS)  # même nom
    assert state["custom_foods"][0]["name"] == "barre MAISON"


def test_a_recipe_cannot_contain_itself():
    state = make_state()
    bowl = copy.deepcopy(state["custom_foods"][1])
    bowl["ingredients"].append({"food": "Menu", "grams": 10})  # Menu contient déjà Bol
    with pytest.raises(ValueError, match="contenir"):
        update_custom_food(state, "Bol", bowl, FOODS)


def test_delete_removes_meals_units_and_is_refused_while_used_in_a_recipe():
    state = make_state()
    with pytest.raises(ValueError, match="Bol"):
        delete_custom_food(state, "Barre maison")
    delete_custom_food(state, "Menu")
    delete_custom_food(state, "Bol")
    delete_custom_food(state, "Barre maison")
    assert state["custom_foods"] == []
    assert state["journal"] == {"2026-09-23": [{"food": "baguette", "grams": 50}]}  # le 24 était vide
    assert state["food_units"] == {} and state["last_units"] == {}
    with pytest.raises(ValueError):
        delete_custom_food(state, "Barre maison")
