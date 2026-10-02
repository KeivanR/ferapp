"""Tests de comparison.py (onglet « Comparer »)."""

from pathlib import Path

import pytest

from comparison import (
    add_food,
    axis_max,
    best_slots,
    compared_grams,
    frequent_foods,
    nutrient_shares,
    portion_for,
    remove_food,
    slot_letter,
    valid_selection,
)
from nutrition import ALL_KEYS, load_foods

FOODS = load_foods(Path(__file__).parent / "foods_demo.csv")
RECOMMENDED = {k: 1000.0 for k in ALL_KEYS} | {"fer": 10.0}


def test_a_food_keeps_its_slot_when_another_is_removed():
    selection = []
    assert add_food(selection, "lentilles cuites", 3)
    assert add_food(selection, "baguette", 3)
    assert not add_food(selection, "BAGUETTE", 3)  # déjà là
    remove_food(selection, "lentilles cuites")
    assert selection == [{"name": "baguette", "slot": 1}]
    assert add_food(selection, "pain complet", 3)  # reprend le slot libéré
    assert selection[-1] == {"name": "pain complet", "slot": 0}
    assert add_food(selection, "quinoa cuit", 3)
    assert not add_food(selection, "riz blanc cuit", 3)  # plein
    assert [slot_letter(s["slot"]) for s in selection] == ["B", "A", "C"]


def test_valid_selection_drops_missing_foods():
    selection = [{"name": "baguette", "slot": 0}, {"name": "aliment supprimé", "slot": 1}]
    assert valid_selection(selection, FOODS) == [{"name": "baguette", "slot": 0}]


def test_portion_and_compared_grams():
    units = {"baguette": [{"label": "tranche", "grams": 30}]}
    assert portion_for("baguette", FOODS, units) == {"label": "tranche", "grams": 30}
    assert portion_for("quinoa cuit", FOODS, units) is None
    assert compared_grams("baguette", FOODS, units, per_portion=True) == 30
    assert compared_grams("baguette", FOODS, units, per_portion=False) == 100
    assert compared_grams("quinoa cuit", FOODS, units, per_portion=True) == 100  # pas de portion connue


def test_nutrient_shares_are_amount_and_share_of_recommendation():
    shares = nutrient_shares("lentilles cuites", 200, FOODS, RECOMMENDED, ["fer"])  # 3,3 mg / 100 g
    assert shares["fer"]["amount"] == pytest.approx(6.6)
    assert shares["fer"]["ratio"] == pytest.approx(0.66)
    no_reference = nutrient_shares("lentilles cuites", 200, FOODS, {"fer": None}, ["fer"])
    assert no_reference["fer"]["amount"] == pytest.approx(6.6) and no_reference["fer"]["ratio"] is None


def test_best_slots():
    shares = {0: {"fer": {"amount": 3.0}}, 1: {"fer": {"amount": 5.0}}, 2: {"fer": {"amount": 5.0}}}
    assert best_slots(shares, "fer") == {1, 2}
    assert best_slots({0: shares[0]}, "fer") == set()  # un seul aliment : rien à comparer
    assert best_slots({0: {"fer": {"amount": 0.0}}, 1: {"fer": {"amount": 0.0}}}, "fer") == set()


def test_axis_max_picks_the_smallest_step_and_respects_the_cap():
    assert axis_max([], cap=2.0) == 0.25
    assert axis_max([0.1, 0.22], cap=2.0) == 0.25
    assert axis_max([0.66], cap=2.0) == 1.0
    assert axis_max([1.2], cap=2.0) == 1.5
    assert axis_max([8.0], cap=2.0) == 2.0  # plafonné
    assert axis_max([8.0], cap=10.0) == 10.0
    assert axis_max([None, 0.4, None], cap=1.0) == 0.5  # nutriments sans repère ignorés


def test_frequent_foods_most_noted_first_and_only_existing():
    journal = {
        "2026-09-23": [{"food": "baguette", "grams": 50}, {"food": "lentilles cuites", "grams": 100}],
        "2026-09-24": [{"food": "Baguette", "grams": 50}, {"food": "aliment supprimé", "grams": 10}],
    }
    assert frequent_foods(journal, FOODS, limit=5) == ["baguette", "lentilles cuites"]
    assert frequent_foods(journal, FOODS, limit=1) == ["baguette"]
