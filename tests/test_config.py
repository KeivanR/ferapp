"""Tests du chargeur de configuration : config.toml est édité à la main, donc validé strictement."""

import textwrap

import pytest

from config import ConfigError, load_config

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
    assert cfg["nutrients"] and set(cfg["references"]) == {n["key"] for n in cfg["nutrients"]}
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
        ('femme_regles = [[200, 16]]', 'femme_regles = [[200, 16]]\nfemme_regle = [[200, 1]]'),  # faute de frappe
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