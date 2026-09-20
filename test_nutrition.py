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
