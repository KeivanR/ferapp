"""Tests du chargeur de configuration : config.toml est édité à la main, donc validé strictement."""

import textwrap

import pytest

from config import ConfigError, load_config, load_default_units, load_resources

VALID = """
[nutrients.fer]
label = "Fer"
unit = "mg"
group = "Minéraux"
csv_column = "fer_mg"
ciqual = ['^Fer \\(mg']
[nutrients.fer.reference]
homme = [[10, 8], [200, 11]]
femme = [[10, 8], [200, 11]]
femme_regles = [[200, 16]]
femme_regles_abondantes = [[200, 20]]
grossesse = 16
"""


def write(tmp_path, text):
    path = tmp_path / "c.toml"
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def test_shipped_config_is_valid():
    cfg = load_config()
    assert cfg["nutrients"]
    assert set(cfg["references"]) == {n["key"] for n in cfg["nutrients"] if n["goal"] is not None}
    assert [g["name"] for g in cfg["groups"]] == list(dict.fromkeys(n["group"] for n in cfg["nutrients"]))
    assert set(cfg["profile"]["default_groups"]) <= {g["name"] for g in cfg["groups"]}
    assert cfg["app"]["foods_file"].endswith(".csv")


def test_minimal_config_uses_defaults(tmp_path):
    cfg = load_config(write(tmp_path, VALID))
    assert cfg["app"]["suggestions_max"] == 8
    assert cfg["profile"]["menstruation_age_range"] == [12, 50]
    n = cfg["nutrients"][0]
    assert (n["key"], n["col"], n["unit"], n["group"]) == ("fer", "fer_mg", "mg", "Minéraux")
    assert cfg["references"]["fer"]["femme_regles"] == [(200, 16)]
    assert cfg["references"]["fer"]["femme_regles_abondantes"] == [(200, 20)]
    assert cfg["references"]["fer"]["grossesse"] == 16
    assert "allaitement" not in cfg["references"]["fer"]


def test_overrides_and_env_variable(tmp_path, monkeypatch):
    path = write(tmp_path, '[app]\ntitle = "Autre"\nsuggestions_max = 3\n' + VALID)
    monkeypatch.setenv("NUTRI_CONFIG", str(path))
    cfg = load_config()  # pas d'argument : la variable d'environnement est utilisée
    assert cfg["app"]["title"] == "Autre" and cfg["app"]["suggestions_max"] == 3


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("femme_regles = [[200, 16]]", "femme_regles = [[200, 16]]\nfemme_regle = [[200, 1]]"),  # faute de frappe
    ],
)
def test_unknown_reference_key_is_rejected(tmp_path, mutation, message):
    with pytest.raises(ConfigError, match="femme_regle"):
        load_config(write(tmp_path, VALID.replace(mutation, message)))


@pytest.mark.parametrize(
    "old, new, expected",
    [
        ("homme = [[10, 8], [200, 11]]\n", "", "« homme » manquant"),
        ("homme = [[10, 8], [200, 11]]", "homme = [[200, 8], [10, 11]]", "strictement croissants"),
        ("femme = [[10, 8], [200, 11]]", "femme = [[10, 8], [100, 11]]", "age_max"),
        ("femme = [[10, 8], [200, 11]]", "femme = [[10, -8], [200, 11]]", ">= 0"),
        ("femme = [[10, 8], [200, 11]]", "femme = [[10, 8, 1], [200, 11]]", "[âge_max, valeur]"),
        ("femme = [[10, 8], [200, 11]]", 'femme = [[10, "8"], [200, 11]]', "nombre"),
        ("grossesse = 16", 'grossesse = "seize"', "nombre"),
        ('csv_column = "fer_mg"', "csv_column = 3", "texte"),
        ('unit = "mg"\n', "", "« unit » manquant"),
        ("ciqual = ['^Fer \\(mg']", "ciqual = [3]", "texte"),
        ('label = "Fer"', 'label = "Fer"\ncouleur = "rouge"', "clés inconnues"),
    ],
)
def test_invalid_nutrient_blocks_are_rejected_with_a_clear_message(tmp_path, old, new, expected):
    assert old in VALID, old
    with pytest.raises(ConfigError, match=expected) as err:
        load_config(write(tmp_path, VALID.replace(old, new)))
    assert "fer" in str(err.value)  # le message dit de quel nutriment il s'agit


def test_duplicate_csv_column_is_rejected(tmp_path):
    second = VALID.replace("[nutrients.fer", "[nutrients.fer2").replace('label = "Fer"', 'label = "Fer bis"')
    with pytest.raises(ConfigError, match="déjà utilisée"):
        load_config(write(tmp_path, VALID + second))


@pytest.mark.parametrize(
    "extra, expected",
    [
        ("[unknown]\nx = 1\n", "Sections inconnues"),
        ("[app]\nnope = 1\n", "clés inconnues"),
        ("[profile]\nage_min = 50\nage_max = 40\n", "age_min"),
        ("[profile]\nmenstruation_age_range = [50, 12]\n", "menstruation_age_range"),
        ("[display]\nring_size = 2\n", "ring_size"),
        ('[foods_build]\nrequired_group = "Inconnu"\n', "aucun groupe"),
        ("[app]\nsuggestions_max = 0\n", "suggestions_max"),
        ("[app]\nhistory_years = 0\n", "history_years"),
        ('[profile]\ndefault_groups = ["Inconnu"]\n', "default_groups"),
        ('[groups."Inconnu"]\nicon = "BOLT"\n', "groupes inconnus"),
        ("[app]\ncompare_max_foods = 50\n", "une couleur par aliment"),
        ("[display]\ncompare_scale_max = 50\n", "compare_scale_max"),
        ("[app]\nweeks_min = 2.5\n", "entier"),
        ("[display]\nswipe_switch_fraction = 3\n", "swipe_switch_fraction"),
    ],
)
def test_invalid_sections_are_rejected(tmp_path, extra, expected):
    with pytest.raises(ConfigError, match=expected):
        load_config(write(tmp_path, extra + VALID))


def test_syntax_error_missing_file_and_no_nutrients(tmp_path):
    with pytest.raises(ConfigError, match="syntaxe TOML"):
        load_config(write(tmp_path, "[app\n"))
    with pytest.raises(ConfigError, match="introuvable"):
        load_config(tmp_path / "absent.toml")
    with pytest.raises(ConfigError, match="Aucun nutriment"):
        load_config(write(tmp_path, '[app]\ntitle = "x"\n'))


# --- config/unites_par_defaut.csv ------------------------------------------------------------
UNITS_HEADER = "alim_code,aliment,unite,grammes\n"


def write_units(tmp_path, rows: str):
    path = tmp_path / "unites.csv"
    path.write_text(UNITS_HEADER + rows, encoding="utf-8")
    return path


def test_shipped_default_units_are_valid():
    units = load_default_units()
    assert len(units) > 2000
    assert all(u is None or (u["label"] and u["grams"] > 0) for u in units.values())


def test_default_units_are_parsed(tmp_path):
    units = load_default_units(
        write_units(tmp_path, '13039,"Kiwi, cru",fruit,75\n7000,Pain (aliment moyen),morceau,"50,5"\n11017,Sel,,\n')
    )
    assert units == {
        "13039": {"label": "fruit", "grams": 75.0},
        "7000": {"label": "morceau", "grams": 50.5},  # virgule décimale acceptée
        "11017": None,  # unité et grammes vides : volontairement aucune unité
    }


@pytest.mark.parametrize(
    "rows, expected",
    [
        ("1,x,fruit,abc\n", "nombre"),
        ("1,x,fruit,0\n", "positif"),
        ("1,x,fruit,-3\n", "positif"),
        ("1,x,,150\n", "vide"),
        ("1,x,Grammes,150\n", "réservé"),
        (",x,fruit,150\n", "alim_code manquant"),
        ("1,x,fruit,150\n1,y,pot,100\n", "deux fois"),
    ],
)
def test_invalid_default_units_are_rejected(tmp_path, rows, expected):
    with pytest.raises(ConfigError, match=expected):
        load_default_units(write_units(tmp_path, rows))


def test_default_units_bad_header_or_missing_file(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("code,unite,grammes\n1,fruit,150\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="colonnes manquantes"):
        load_default_units(bad)
    with pytest.raises(ConfigError, match="introuvable"):
        load_default_units(tmp_path / "absent.csv")


# --- config/ressources.toml ------------------------------------------------------------------
def write_resources(tmp_path, text: str):
    path = tmp_path / "ressources.toml"
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def test_shipped_resources_are_valid():
    resources = load_resources()
    assert resources["links"] and resources["faq"]


def test_resources_are_parsed(tmp_path):
    resources = load_resources(
        write_resources(
            tmp_path,
            """
            [[links]]
            group = "Fer"
            title = "Un lien"
            url = "https://exemple.fr"

            [[faq]]
            question = "Pourquoi ?"
            answer = "Parce que."
            """,
        )
    )
    assert resources == {
        "links": [{"group": "Fer", "title": "Un lien", "url": "https://exemple.fr", "description": ""}],
        "faq": [{"question": "Pourquoi ?", "answer": "Parce que."}],
    }


@pytest.mark.parametrize(
    "text, expected",
    [
        ('[[links]]\ngroup = "g"\ntitle = "t"\n', "url"),  # clé obligatoire manquante
        ('[[links]]\ngroup = "g"\ntitle = "t"\nurl = "exemple.fr"\n', "http"),  # pas un lien web
        ('[[faq]]\nquestion = "q"\nanswer = ""\n', "answer"),  # réponse vide
        ('[[faq]]\nquestion = "q"\nanswer = "r"\ncouleur = "rouge"\n', "clés inconnues"),
        ('[[faq]]\nquestion = 3\nanswer = "r"\n', "texte"),
        ('[[videos]]\ntitle = "t"\n', "blocs inconnus"),
    ],
)
def test_invalid_resources_are_rejected(tmp_path, text, expected):
    with pytest.raises(ConfigError, match=expected):
        load_resources(write_resources(tmp_path, text))


def test_goal_and_missing_reference(tmp_path):
    """Un nutriment peut être à limiter (goal = "max") ou sans repère (pas de bloc reference)."""
    extra = """
        [nutrients.sel]
        label = "Sel"
        unit = "g"
        group = "Minéraux"
        csv_column = "sel_g"
        goal = "max"
        [nutrients.sel.reference]
        homme = [[200, 5]]
        femme = [[200, 5]]

        [nutrients.fructose]
        label = "Fructose"
        unit = "g"
        group = "Minéraux"
        csv_column = "fructose_g"
    """
    cfg = load_config(write(tmp_path, VALID + extra))
    goals = {n["key"]: n["goal"] for n in cfg["nutrients"]}
    assert goals["fer"] == "min" and goals["sel"] == "max" and goals["fructose"] is None
    assert "fructose" not in cfg["references"] and cfg["references"]["sel"]["homme"] == [(200, 5)]
    with pytest.raises(ConfigError, match="goal"):
        load_config(write(tmp_path, VALID + extra + '        goal = "max"\n'))  # goal sans reference
    with pytest.raises(ConfigError, match="goal"):
        load_config(write(tmp_path, VALID + extra.replace('goal = "max"', 'goal = "plafond"')))


def test_groups_get_description_and_icon(tmp_path):
    cfg = load_config(write(tmp_path, '[groups."Minéraux"]\ndescription = "Fer et compagnie"\n' + VALID))
    assert cfg["groups"] == [{"name": "Minéraux", "description": "Fer et compagnie", "icon": "CATEGORY_OUTLINED"}]
