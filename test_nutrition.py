from pathlib import Path

import pytest

from nutrition import (
    Profile,
    completion,
    daily_totals,
    find_food,
    load_foods,
    normalize,
    parse_grams,
    recommended_intakes,
    search_foods,
)

FOODS = load_foods(Path(__file__).parent / "foods_demo.csv")


def test_csv_loads_all_nutrients():
    assert len(FOODS) > 30
    lentilles = FOODS["lentilles cuites"]["per100"]
    assert lentilles["fer"] == pytest.approx(3.3)


def test_normalize_and_search_ignore_accents():
    assert normalize("  Épinards   CUITS ") == "epinards cuits"
    assert "epinards cuits" in [normalize(n) for n in search_foods("épin", FOODS)]
    assert search_foods("", FOODS) == []


def test_find_food():
    assert find_food("Lentilles cuites", FOODS)["name"] == "lentilles cuites"
    assert find_food("epinard", FOODS)["name"] == "epinards cuits"  # résultat unique
    assert find_food("xyz", FOODS) is None


def test_parse_grams():
    assert parse_grams("150") == 150
    assert parse_grams("150 g") == 150
    assert parse_grams("150,5") == 150.5
    assert parse_grams("abc") is None
    assert parse_grams("0") is None
    assert parse_grams("-3") is None


def test_daily_totals_scale_with_grams():
    entries = [{"food": "lentilles cuites", "grams": 200}]
    totals = daily_totals(entries, FOODS)
    assert totals["fer"] == pytest.approx(6.6)
    assert totals["calcium"] == pytest.approx(38)


def test_recommended_depends_on_profile():
    woman = recommended_intakes(Profile(age=30, sex="F"))
    man = recommended_intakes(Profile(age=30, sex="H"))
    assert woman["fer"] > man["fer"]
    pregnant = recommended_intakes(Profile(age=30, sex="F", pregnant=True))
    assert pregnant["iode"] == 200
    breastfeeding = recommended_intakes(Profile(age=30, sex="F", breastfeeding=True))
    assert breastfeeding["selenium"] == 85
    # grossesse ignorée pour un homme
    assert recommended_intakes(Profile(age=30, sex="H", pregnant=True)) == man


def test_completion_can_exceed_one():
    rec = recommended_intakes(Profile(age=30, sex="H"))
    ratios = completion(daily_totals([{"food": "boudin noir", "grams": 200}], FOODS), rec)
    assert ratios["fer"] > 1
    assert ratios["calcium"] < 0.1


# --- conversion Ciqual -------------------------------------------------------
from build_foods import parse_value


def test_parse_value_ciqual_formats():
    assert parse_value("2,45") == pytest.approx(2.45)
    assert parse_value("-") is None
    assert parse_value(None) is None
    assert parse_value("traces") == 0
    assert parse_value("< 0,25") == 0
    assert parse_value("<\n0,0005") == 0
    assert parse_value(3) == 3.0


def test_real_ciqual_csv_if_present():
    path = Path(__file__).parent / "foods.csv"
    if not path.exists():
        pytest.skip("foods.csv non généré")
    foods = load_foods(path)
    assert len(foods) > 2000
    assert any("Lentille verte, bouillie" in f["name"] for f in foods.values())
    hits = search_foods("lentille", foods)
    assert hits and all("lentille" in normalize(h) for h in hits)
    # les plus courts d'abord
    assert len(hits[0]) <= len(hits[-1])


# --- choix des nutriments dans le profil -------------------------------------
from nutrition import ALL_KEYS, selected_nutrients


def test_profile_defaults_to_all_nutrients():
    assert Profile().nutrients == ALL_KEYS
    # ancien profil sauvegardé sans le champ "nutrients"
    old = {"age": 30, "sex": "F", "pregnant": False, "breastfeeding": False}
    assert Profile.from_dict(old).nutrients == ALL_KEYS


def test_profile_nutrients_roundtrip_and_order():
    p = Profile(nutrients=["zinc", "fer"])
    p2 = Profile.from_dict(p.to_dict())
    assert p2.nutrients == ["zinc", "fer"]
    # l'affichage suit l'ordre de NUTRIENTS, pas l'ordre du clic
    assert [n["key"] for n in selected_nutrients(p2)] == ["fer", "zinc"]


def test_profile_ignores_unknown_and_empty_selection():
    assert Profile.from_dict({"nutrients": ["fer", "inconnu"]}).nutrients == ["fer"]
    assert Profile.from_dict({"nutrients": []}).nutrients == ALL_KEYS


# --- vitamines ---------------------------------------------------------------
def test_every_nutrient_has_reference_and_group():
    from nutrition import NUTRIENTS, REFERENCES

    for n in NUTRIENTS:
        assert n["key"] in REFERENCES, n["key"]
        assert n["group"] in ("Minéraux", "Vitamines")
        assert set(REFERENCES[n["key"]]) >= {"H", "F"}
    assert {n["group"] for n in NUTRIENTS} == {"Minéraux", "Vitamines"}


def test_vitamin_references_depend_on_profile():
    woman = recommended_intakes(Profile(age=30, sex="F"))
    man = recommended_intakes(Profile(age=30, sex="H"))
    assert woman["vitamine_c"] < man["vitamine_c"]
    assert woman["vitamine_d"] == man["vitamine_d"] == 15
    assert recommended_intakes(Profile(age=30, sex="F", pregnant=True))["vitamine_b9"] == 600
    assert recommended_intakes(Profile(age=30, sex="F", breastfeeding=True))["vitamine_a"] == 1300


def test_real_csv_has_vitamins():
    path = Path(__file__).parent / "foods.csv"
    if not path.exists():
        pytest.skip("foods.csv non généré")
    foods = load_foods(path)
    kiwi = foods[normalize("Kiwi, chair sans peau, avec pépins, cru")]["per100"]
    assert kiwi["vitamine_c"] > 50
    smoked = foods[normalize("Saumon fumé")]["per100"]
    assert smoked["vitamine_d"] > 3
    assert smoked["vitamine_b12"] > 2


# --- nutriment le plus apporté par une entrée --------------------------------
def test_top_nutrient_uses_share_of_recommendation_not_raw_amount():
    from nutrition import NUTRIENTS, selected_nutrients, top_nutrient

    profile = Profile(age=30, sex="F")
    rec = recommended_intakes(profile)
    entry = {"food": "lentilles cuites", "grams": 100}
    top = top_nutrient(entry, FOODS, rec, NUTRIENTS)
    # le potassium a la plus grosse quantité brute (369 mg) mais le fer pèse plus (3,3/16)
    assert top["key"] == "fer"
    assert top["amount"] == pytest.approx(3.3)
    assert top["unit"] == "mg"
    assert top["share"] == pytest.approx(3.3 / 16)


def test_top_nutrient_only_among_chosen_nutrients_and_scales_with_grams():
    from nutrition import selected_nutrients, top_nutrient

    profile = Profile(age=30, sex="F", nutrients=["calcium", "potassium"])
    rec = recommended_intakes(profile)
    chosen = selected_nutrients(profile)
    top = top_nutrient({"food": "lentilles cuites", "grams": 200}, FOODS, rec, chosen)
    assert top["key"] == "potassium"  # 738/3500 > 38/950
    assert top["amount"] == pytest.approx(738)


def test_top_nutrient_none_without_data():
    from nutrition import NUTRIENTS, top_nutrient

    rec = recommended_intakes(Profile())
    assert top_nutrient({"food": "inconnu", "grams": 100}, FOODS, rec, NUTRIENTS) is None
    assert top_nutrient({"food": "lentilles cuites", "grams": 100}, FOODS, rec, []) is None


# --- colonnes de repli à la conversion ---------------------------------------
def test_resolve_uses_fallback_and_sums():
    from build_foods import resolve

    row = ["-", "50,5", "1,5", "2"]
    assert resolve(row, [[0], [1]]) == pytest.approx(50.5)  # 1re vide -> repli
    assert resolve(row, [[1], [0]]) == pytest.approx(50.5)  # 1re renseignée l'emporte
    assert resolve(row, [[2, 3]]) == pytest.approx(3.5)  # somme (ex. D2 + D3)
    assert resolve(["-", None], [[0], [1]]) is None
    assert resolve(["< 0,5", "9"], [[0], [1]]) == 0  # "< x" = 0 mais bien renseigné


def test_real_csv_vitamin_coverage_and_lentils():
    path = Path(__file__).parent / "foods.csv"
    if not path.exists():
        pytest.skip("foods.csv non généré")
    import csv

    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    for col in ("vitamine_b9_ug", "vitamine_e_mg", "vitamine_d_ug"):
        assert sum(1 for r in rows if r[col] != "") > 2000, col
    lentils = next(r for r in rows if r["aliment"].startswith("Lentille verte, bouillie"))
    assert float(lentils["vitamine_b9_ug"]) > 0


# --- aliments personnalisés ---------------------------------------------------
def test_official_foods_are_not_custom():
    assert all(f["custom"] is False for f in FOODS.values())


def test_parse_nutrient_value():
    from nutrition import parse_nutrient_value

    assert parse_nutrient_value("") == 0.0
    assert parse_nutrient_value("  ") == 0.0
    assert parse_nutrient_value("3,5") == pytest.approx(3.5)
    assert parse_nutrient_value("0") == 0.0
    assert parse_nutrient_value("abc") is None
    assert parse_nutrient_value("-2") is None


def test_recipe_per100_sums_and_scales():
    from nutrition import recipe_per100

    ings = [
        {"food": "lentilles cuites", "grams": 200},  # fer 6.6 mg
        {"food": "boudin noir", "grams": 100},  # fer 22 mg
    ]
    per100 = recipe_per100(ings, FOODS)
    assert per100["fer"] == pytest.approx((6.6 + 22) / 300 * 100)
    # poids final plus faible (évaporation) -> plat plus concentré
    assert recipe_per100(ings, FOODS, final_weight=250)["fer"] == pytest.approx((6.6 + 22) / 250 * 100)
    assert set(per100) == set(ALL_KEYS)


def test_recipe_per100_errors():
    from nutrition import recipe_per100

    with pytest.raises(ValueError):
        recipe_per100([], FOODS)
    with pytest.raises(ValueError):
        recipe_per100([{"food": "inconnu", "grams": 10}], FOODS)


def test_merge_foods_flags_custom_and_computes_entries():
    from nutrition import merge_foods

    custom = [{"name": "Barre maison", "kind": "manual", "per100": {"fer": 5.0, "calcium": 100.0}}]
    merged = merge_foods(FOODS, custom)
    food = merged[normalize("barre maison")]
    assert food["custom"] is True
    assert food["per100"]["fer"] == 5.0
    assert food["per100"]["zinc"] == 0.0  # nutriment non renseigné -> 0
    totals = daily_totals([{"food": "Barre maison", "grams": 50}], merged)
    assert totals["fer"] == pytest.approx(2.5)
    assert normalize("barre maison") not in FOODS  # la base officielle n'est pas modifiée


def test_custom_foods_come_first_in_search():
    from nutrition import merge_foods

    custom = [{"name": "Lentilles de ma grand-mère, bien longues", "kind": "manual", "per100": {}}]
    merged = merge_foods(FOODS, custom)
    hits = search_foods("lentilles", merged)
    assert hits[0] == "Lentilles de ma grand-mère, bien longues"
    assert merged[normalize(hits[0])]["custom"] is True
    assert all(not merged[normalize(h)]["custom"] for h in hits[1:])


def test_storage_defaults_and_old_files(tmp_path, monkeypatch):
    import json

    import storage

    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(tmp_path))
    assert storage.load_state() == {"profile": None, "journal": {}, "custom_foods": []}
    # ancien fichier sans "custom_foods"
    (tmp_path / "state.json").write_text(json.dumps({"profile": {"age": 30}, "journal": {}}))
    state = storage.load_state()
    assert state["custom_foods"] == [] and state["profile"] == {"age": 30}
    state["custom_foods"].append({"name": "x", "per100": {}})
    storage.save_state(state)
    assert storage.load_state()["custom_foods"][0]["name"] == "x"