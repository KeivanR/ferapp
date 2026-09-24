from pathlib import Path

import pytest

from build_foods import parse_value
from nutrition import (
    ALL_KEYS,
    WOMAN_STATUSES,
    Profile,
    completion,
    daily_totals,
    find_food,
    load_foods,
    normalize,
    parse_grams,
    recommended_intakes,
    search_foods,
    selected_nutrients,
)

ROOT = Path(__file__).parent.parent
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


# Configuration de test : on vérifie la LOGIQUE de choix de la référence, pas les valeurs
# de config.toml (que tu peux modifier librement).
TEST_NUTRIENTS = [{"key": "fer"}, {"key": "zinc"}, {"key": "calcium"}]
TEST_REFS = {
    "fer": {
        "homme": [(3, 7), (200, 11)],
        "femme": [(3, 7), (200, 11)],
        "femme_regles": [(3, 7), (200, 16)],
        "femme_regles_abondantes": [(3, 7), (200, 20)],
        "grossesse": 15,
        "allaitement": 10,
    },
    "zinc": {"homme": [(200, 10)], "femme": [(200, 8)], "grossesse": 9.5, "allaitement": 12},
    "calcium": {"homme": [(200, 900)], "femme": [(200, 900)]},
    # « règles » défini, mais pas « règles abondantes » : celle-ci doit se rabattre sur « règles »
    "iode": {"homme": [(200, 150)], "femme": [(200, 150)], "femme_regles": [(200, 160)]},
}


def rec(**profile_kwargs):
    return recommended_intakes(Profile(**profile_kwargs), references=TEST_REFS, nutrients=TEST_NUTRIENTS)


def rec_iode(**profile_kwargs):
    return recommended_intakes(Profile(**profile_kwargs), references=TEST_REFS, nutrients=[{"key": "iode"}])["iode"]


def test_recommended_depends_on_sex_and_age():
    assert rec(age=30, sex="H")["zinc"] == 10
    assert rec(age=30, sex="F", status="non_reglee")["zinc"] == 8
    assert rec(age=2, sex="F", status="reglee")["fer"] == 7  # tranche d'âge : enfant


def test_each_woman_status_uses_its_own_reference():
    fer = {s: rec(age=30, sex="F", status=s)["fer"] for s in WOMAN_STATUSES}
    assert fer == {"non_reglee": 11, "reglee": 16, "abondante": 20, "enceinte": 15, "allaitement": 10}
    zinc = {s: rec(age=30, sex="F", status=s)["zinc"] for s in WOMAN_STATUSES}
    # zinc : pas de valeur règles -> « femme » ; grossesse et allaitement définis
    assert zinc == {"non_reglee": 8, "reglee": 8, "abondante": 8, "enceinte": 9.5, "allaitement": 12}


def test_missing_reference_falls_back():
    calcium = {s: rec(age=30, sex="F", status=s)["calcium"] for s in WOMAN_STATUSES}
    assert set(calcium.values()) == {900}  # aucune clé spécifique : « femme » partout
    assert rec_iode(age=30, sex="F", status="abondante") == 160  # abondante -> règles
    assert rec_iode(age=30, sex="F", status="reglee") == 160
    assert rec_iode(age=30, sex="F", status="enceinte") == 150  # pas de grossesse -> femme


def test_status_default_is_guessed_from_age():
    assert Profile(age=30, sex="F").effective_status() == "reglee"  # dans menstruation_age_range
    assert Profile(age=60, sex="F").effective_status() == "non_reglee"
    assert Profile(age=2, sex="F").effective_status() == "non_reglee"
    assert rec(age=30, sex="F")["fer"] == 16 and rec(age=60, sex="F")["fer"] == 11
    # la réponse du profil l'emporte sur l'estimation
    assert rec(age=60, sex="F", status="reglee")["fer"] == 16
    assert rec(age=30, sex="F", status="non_reglee")["fer"] == 11


def test_men_ignore_status():
    man = rec(age=30, sex="H")
    for status in WOMAN_STATUSES:
        assert rec(age=30, sex="H", status=status) == man
    assert Profile(age=30, sex="H", status="enceinte").effective_status() is None


def test_profile_status_roundtrip():
    p = Profile(age=50, sex="F", status="abondante")
    assert Profile.from_dict(p.to_dict()).status == "abondante"
    assert Profile.from_dict(Profile(age=30).to_dict()).status is None
    assert Profile.from_dict({"status": "n'importe quoi"}).status is None  # valeur inconnue ignorée


def test_old_profiles_are_migrated():
    """Anciens fichiers : cases séparées pregnant / breastfeeding / menstruating."""
    base = {"age": 30, "sex": "F"}
    assert Profile.from_dict(base).status is None  # ni case ni réponse : estimée d'après l'âge
    assert Profile.from_dict({**base, "pregnant": True}).status == "enceinte"
    assert Profile.from_dict({**base, "breastfeeding": True}).status == "allaitement"
    assert Profile.from_dict({**base, "pregnant": True, "breastfeeding": True}).status == "allaitement"
    assert Profile.from_dict({**base, "menstruating": True}).status == "reglee"
    assert Profile.from_dict({**base, "menstruating": False}).status == "non_reglee"
    assert Profile.from_dict({**base, "pregnant": True, "menstruating": True}).status == "enceinte"


def test_shipped_config_status_ordering():
    """Sanity check sur config.toml : plus de pertes ne baisse jamais la référence."""
    from nutrition import NUTRIENTS

    for age in (12, 25, 45):
        r = {s: recommended_intakes(Profile(age=age, sex="F", status=s)) for s in ("non_reglee", "reglee", "abondante")}
        assert all(r["reglee"][n["key"]] >= r["non_reglee"][n["key"]] for n in NUTRIENTS), age
        assert all(r["abondante"][n["key"]] >= r["reglee"][n["key"]] for n in NUTRIENTS), age


def test_completion_can_exceed_one():
    from nutrition import NUTRIENTS

    rec_ = {n["key"]: 100.0 for n in NUTRIENTS} | {"fer": 11.0, "calcium": 950.0}
    ratios = completion(daily_totals([{"food": "boudin noir", "grams": 200}], FOODS), rec_)
    assert ratios["fer"] > 1
    assert ratios["calcium"] < 0.1


# --- conversion Ciqual -------------------------------------------------------


def test_parse_value_ciqual_formats():
    assert parse_value("2,45") == pytest.approx(2.45)
    assert parse_value("-") is None
    assert parse_value(None) is None
    assert parse_value("traces") == 0
    assert parse_value("< 0,25") == 0
    assert parse_value("<\n0,0005") == 0
    assert parse_value(3) == 3.0


def test_parse_value_uses_config_options():
    assert parse_value("< 0,25", below_limit_factor=0.5) == pytest.approx(0.125)
    assert parse_value("<\n0,5", below_limit_factor=1) == pytest.approx(0.5)
    assert parse_value("<", below_limit_factor=1) == 0.0
    assert parse_value("traces", traces_value=0.1) == pytest.approx(0.1)


def test_real_ciqual_csv_if_present():
    path = ROOT / "foods.csv"
    if not path.exists():
        pytest.skip("foods.csv non généré")
    foods = load_foods(path)
    assert len(foods) > 2000
    assert any("Lentille verte, bouillie" in f["name"] for f in foods.values())
    hits = search_foods("pain", foods)
    assert hits[0] == "Pain (aliment moyen)"
    hits = search_foods("lentille", foods)
    assert hits and all("lentille" in normalize(h) for h in hits)
    assert "(aliment moyen)" in hits[0]


# --- « aliment moyen » proposé en premier (config Ciqual, voir search_foods) -----------------
def test_search_foods_ranks_aliment_moyen_first():
    foods = load_foods(Path(__file__).parent / "foods_demo.csv")
    foods = dict(foods)
    for name in ("Pain complet", "Pain (aliment moyen)", "Pain aux céréales"):
        foods[normalize(name)] = {"name": name, "per100": {}, "custom": False}

    hits = search_foods("pain", foods)
    assert hits[0] == "Pain (aliment moyen)"


def test_search_foods_custom_food_still_ranks_before_aliment_moyen():
    foods = load_foods(Path(__file__).parent / "foods_demo.csv")
    foods = dict(foods)
    foods[normalize("Pain (aliment moyen)")] = {
        "name": "Pain (aliment moyen)",
        "per100": {},
        "custom": False,
    }
    foods[normalize("Pain maison")] = {"name": "Pain maison", "per100": {}, "custom": True}

    hits = search_foods("pain", foods)
    assert hits[0] == "Pain maison"
    assert hits[1] == "Pain (aliment moyen)"


def test_search_foods_no_aliment_moyen_is_unaffected():
    # "lentilles cuites" (foods_demo.csv) n'a pas de variante "(aliment moyen)" :
    # le classement retombe simplement sur le nom le plus court.
    hits = search_foods("lentille", FOODS)
    assert hits == ["lentilles cuites"]


# --- choix des nutriments dans le profil -------------------------------------


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
    from config import BAND_KEYS, SCALAR_KEYS
    from nutrition import AGE_MAX, NUTRIENTS, REFERENCES

    assert NUTRIENTS
    for n in NUTRIENTS:
        ref = REFERENCES[n["key"]]
        assert n["group"] and n["label"] and n["unit"] and n["col"]
        assert set(ref) >= {"homme", "femme"}
        assert set(ref) <= set(BAND_KEYS) | set(SCALAR_KEYS)
        assert ref["homme"][-1][0] >= AGE_MAX  # toutes les tranches d'âge sont couvertes


def test_real_csv_has_vitamins():
    path = ROOT / "foods.csv"
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
    from nutrition import NUTRIENTS, top_nutrient

    recs = {n["key"]: 1e9 for n in NUTRIENTS} | {
        "fer": 16, "calcium": 950, "magnesium": 300, "zinc": 9, "potassium": 3500, "iode": 150, "selenium": 70,
    }
    entry = {"food": "lentilles cuites", "grams": 100}
    top = top_nutrient(entry, FOODS, recs, NUTRIENTS)
    # le potassium a la plus grosse quantité brute (369 mg) mais le fer pèse plus (3,3/16)
    assert top["key"] == "fer"
    assert top["amount"] == pytest.approx(3.3)
    assert top["unit"] == "mg"
    assert top["share"] == pytest.approx(3.3 / 16)


def test_top_nutrient_only_among_chosen_nutrients_and_scales_with_grams():
    from nutrition import selected_nutrients, top_nutrient

    profile = Profile(age=30, sex="F", nutrients=["calcium", "potassium"])
    recs = {"calcium": 950, "potassium": 3500}
    chosen = selected_nutrients(profile)
    top = top_nutrient({"food": "lentilles cuites", "grams": 200}, FOODS, recs, chosen)
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
    path = ROOT / "foods.csv"
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
    assert storage.load_state() == {
        "profile": None, "journal": {}, "custom_foods": [], "food_units": {}, "last_units": {}
    }
    # ancien fichier sans "custom_foods" ni "food_units"
    (tmp_path / "state.json").write_text(json.dumps({"profile": {"age": 30}, "journal": {}}))
    state = storage.load_state()
    assert state["custom_foods"] == [] and state["profile"] == {"age": 30} and state["food_units"] == {}
    state["custom_foods"].append({"name": "x", "per100": {}})
    storage.save_state(state)
    assert storage.load_state()["custom_foods"][0]["name"] == "x"


# --- unités familières (ex. « 1 assiette » = 250 g) ---------------------------
def test_units_for_food_empty_when_unknown_or_undefined():
    from nutrition import units_for_food

    assert units_for_food("xyz", FOODS, {}) == []
    assert units_for_food("lentilles cuites", FOODS, {}) == []


def test_add_food_unit_then_visible_in_units_for_food():
    from nutrition import add_food_unit, units_for_food

    food_units: dict[str, list[dict]] = {}
    unit = add_food_unit("lentilles cuites", "assiette", 250, FOODS, food_units)
    assert unit == {"label": "assiette", "grams": 250}
    assert units_for_food("lentilles cuites", FOODS, food_units) == [{"label": "assiette", "grams": 250}]
    # un autre aliment n'est pas affecté
    assert units_for_food("boudin noir", FOODS, food_units) == []


def test_add_food_unit_errors():
    from nutrition import add_food_unit

    food_units: dict[str, list[dict]] = {}
    with pytest.raises(ValueError):
        add_food_unit("xyz", "part", 100, FOODS, food_units)  # aliment inconnu
    with pytest.raises(ValueError):
        add_food_unit("lentilles cuites", "", 100, FOODS, food_units)  # nom vide
    with pytest.raises(ValueError):
        add_food_unit("lentilles cuites", "Grammes", 100, FOODS, food_units)  # réservé (insensible casse/accents)
    with pytest.raises(ValueError):
        add_food_unit("lentilles cuites", "assiette", 0, FOODS, food_units)  # grammes non positifs
    with pytest.raises(ValueError):
        add_food_unit("lentilles cuites", "assiette", -5, FOODS, food_units)
    add_food_unit("lentilles cuites", "assiette", 250, FOODS, food_units)
    with pytest.raises(ValueError):
        add_food_unit("lentilles cuites", "Assiette", 300, FOODS, food_units)  # doublon insensible casse


# --- unité par défaut de chaque aliment (config/unites_par_defaut.csv) --------------------------
# Base de test avec des codes Ciqual, et un fichier d'unités fictif passé explicitement.
CODED_FOODS = {
    "kiwi, cru": {"name": "Kiwi, cru", "code": "13039", "per100": {}, "custom": False},
    "sel": {"name": "Sel", "code": "11017", "per100": {}, "custom": False},
    "mystere": {"name": "Mystère", "code": "99999", "per100": {}, "custom": False},
    "gateau maison": {"name": "Gâteau maison", "code": None, "per100": {}, "custom": True},
}
TEST_UNITS = {"13039": {"label": "fruit", "grams": 75.0}, "11017": None}


def test_default_unit_for_uses_code():
    from nutrition import default_unit_for

    assert default_unit_for("kiwi, cru", CODED_FOODS, TEST_UNITS) == {"label": "fruit", "grams": 75.0}
    assert default_unit_for("sel", CODED_FOODS, TEST_UNITS) is None  # volontairement sans unité
    assert default_unit_for("mystere", CODED_FOODS, TEST_UNITS) is None  # absent du fichier
    assert default_unit_for("gateau maison", CODED_FOODS, TEST_UNITS) is None  # perso : pas de code
    assert default_unit_for("xyz", CODED_FOODS, TEST_UNITS) is None  # aliment inconnu
    assert default_unit_for("lentilles cuites", FOODS) is None  # base de démo : pas de codes


def test_default_unit_for_returns_a_copy():
    from nutrition import default_unit_for

    default_unit_for("kiwi, cru", CODED_FOODS, TEST_UNITS)["grams"] = 1
    assert TEST_UNITS["13039"]["grams"] == 75.0


def test_units_for_food_includes_default_unit_first():
    from nutrition import units_for_food

    assert units_for_food("kiwi, cru", CODED_FOODS, {}, TEST_UNITS) == [{"label": "fruit", "grams": 75.0}]


def test_units_for_food_user_unit_overrides_default_grams():
    from nutrition import add_food_unit, units_for_food

    food_units: dict[str, list[dict]] = {}
    add_food_unit("kiwi, cru", "Fruit", 90, CODED_FOODS, food_units)
    units = units_for_food("kiwi, cru", CODED_FOODS, food_units, TEST_UNITS)
    assert units == [{"label": "Fruit", "grams": 90}]  # une seule entrée : remplacée


def test_units_for_food_user_adds_extra_unit_alongside_default():
    from nutrition import add_food_unit, units_for_food

    food_units: dict[str, list[dict]] = {}
    add_food_unit("kiwi, cru", "barquette", 500, CODED_FOODS, food_units)
    units = units_for_food("kiwi, cru", CODED_FOODS, food_units, TEST_UNITS)
    assert units == [{"label": "fruit", "grams": 75.0}, {"label": "barquette", "grams": 500}]


def test_every_ciqual_food_has_a_default_unit():
    """Chaque aliment de foods.csv a une ligne dans config/unites_par_defaut.csv (à compléter
    après une mise à jour Ciqual : build_foods.py liste les manquants)."""
    path = ROOT / "foods.csv"
    if not path.exists():
        pytest.skip("foods.csv non généré")
    pytest.importorskip("openpyxl")  # build_foods l'importe
    from build_foods import foods_without_default_unit
    from nutrition import default_unit_for

    assert foods_without_default_unit(path) == []
    foods = load_foods(path)
    assert default_unit_for("Pain (aliment moyen)", foods) == {"label": "morceau", "grams": 50.0}
    kiwi = default_unit_for("Kiwi, chair sans peau, avec pépins, cru", foods)
    assert kiwi["label"] == "fruit" and 50 <= kiwi["grams"] <= 120


# --- unité présélectionnée : la dernière utilisée, sinon l'unité par défaut -------------------
KIWI_UNITS = [{"label": "fruit", "grams": 75.0}, {"label": "barquette", "grams": 500}]


def test_preferred_unit_is_default_unit_when_never_used():
    from nutrition import GRAMS_UNIT, preferred_unit

    assert preferred_unit("kiwi, cru", CODED_FOODS, KIWI_UNITS, {}) == "fruit"
    assert preferred_unit("kiwi, cru", CODED_FOODS, [], {}) == GRAMS_UNIT  # aucune unité familière
    assert preferred_unit("xyz", CODED_FOODS, KIWI_UNITS, {}) == GRAMS_UNIT  # aliment inconnu


def test_preferred_unit_is_last_used_one():
    from nutrition import GRAMS_UNIT, preferred_unit, remember_unit

    last_units: dict[str, str] = {}
    remember_unit("Kiwi, CRU", "barquette", CODED_FOODS, last_units)  # clé normalisée
    assert last_units == {"kiwi, cru": "barquette"}
    assert preferred_unit("kiwi, cru", CODED_FOODS, KIWI_UNITS, last_units) == "barquette"
    remember_unit("kiwi, cru", GRAMS_UNIT, CODED_FOODS, last_units)  # les grammes se retiennent aussi
    assert preferred_unit("kiwi, cru", CODED_FOODS, KIWI_UNITS, last_units) == GRAMS_UNIT


def test_preferred_unit_falls_back_when_last_unit_is_gone():
    from nutrition import preferred_unit

    last_units = {"kiwi, cru": "Barquette"}
    assert preferred_unit("kiwi, cru", CODED_FOODS, KIWI_UNITS, last_units) == "barquette"  # casse ignorée
    assert preferred_unit("kiwi, cru", CODED_FOODS, KIWI_UNITS[:1], last_units) == "fruit"  # disparue


def test_remember_unit_ignores_unknown_food():
    from nutrition import remember_unit

    last_units: dict[str, str] = {}
    remember_unit("xyz", "fruit", CODED_FOODS, last_units)
    assert last_units == {}
