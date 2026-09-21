"""Chargement et validation de config.toml (références, nutriments, réglages d'affichage).

Le fichier est édité à la main : on vérifie tout au chargement et on lève une ConfigError
qui dit exactement où est le problème, plutôt que d'afficher plus tard de faux chiffres.

Autre fichier possible : variable d'environnement NUTRI_CONFIG (ou argument `path`).
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "config.toml"

# Clés autorisées dans [nutrients.<clé>.reference]
BAND_KEYS = ("homme", "femme", "femme_regles", "femme_regles_abondantes")  # tranches d'âge [[âge_max, valeur], ...]
SCALAR_KEYS = ("grossesse", "allaitement")  # valeur unique
REQUIRED_BANDS = ("homme", "femme")

APP_DEFAULTS = {"title": "Nutri-Suivi", "foods_file": "foods.csv", "suggestions_max": 8}
PROFILE_DEFAULTS = {
    "default_age": 30,
    "age_min": 1,
    "age_max": 120,
    "menstruation_age_range": [12, 50],
}
DISPLAY_DEFAULTS = {
    "ring_size": 88,
    "ring_stroke_width": 9,
    "color_todo": "#FB8C00",
    "color_done": "#43A047",
    "color_custom_food": "#EF6C00",
}
BUILD_DEFAULTS = {"required_group": "Minéraux", "below_limit_factor": 0.0, "traces_value": 0.0}


class ConfigError(ValueError):
    """Erreur dans config.toml."""


def _number(value, where: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{where} : un nombre est attendu (reçu {value!r})")
    if minimum is not None and value < minimum:
        raise ConfigError(f"{where} : doit être >= {minimum} (reçu {value})")
    return value


def _section(raw: dict, name: str, defaults: dict) -> dict:
    section = raw.get(name, {})
    if not isinstance(section, dict):
        raise ConfigError(f"[{name}] doit être une table")
    unknown = set(section) - set(defaults)
    if unknown:
        raise ConfigError(f"[{name}] : clés inconnues {sorted(unknown)} (autorisées : {sorted(defaults)})")
    return {**defaults, **section}


def _bands(value, where: str, age_max: int) -> list[tuple[float, float]]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{where} : liste de tranches [[âge_max, valeur], ...] attendue")
    bands: list[tuple[float, float]] = []
    for i, band in enumerate(value):
        if not isinstance(band, list) or len(band) != 2:
            raise ConfigError(f"{where}, tranche n°{i + 1} : [âge_max, valeur] attendu (reçu {band!r})")
        age = _number(band[0], f"{where}, tranche n°{i + 1}, âge", minimum=0)
        val = _number(band[1], f"{where}, tranche n°{i + 1}, valeur", minimum=0)
        if bands and age <= bands[-1][0]:
            raise ConfigError(
                f"{where} : les âges doivent être strictement croissants ({bands[-1][0]} puis {age})"
            )
        bands.append((age, val))
    if bands[-1][0] < age_max:
        raise ConfigError(
            f"{where} : la dernière tranche s'arrête à {bands[-1][0]} ans, "
            f"elle doit aller au moins jusqu'à age_max = {age_max}"
        )
    return bands


def _ciqual(value, where: str) -> list:
    """Liste d'expressions régulières ; une sous-liste d'expressions = valeurs additionnées."""
    if not isinstance(value, list):
        raise ConfigError(f"{where} : liste attendue")
    for alt in value:
        ok = isinstance(alt, str) or (
            isinstance(alt, list) and alt and all(isinstance(p, str) for p in alt)
        )
        if not ok:
            raise ConfigError(f"{where} : chaque élément doit être un texte ou une liste de textes (reçu {alt!r})")
    return value


def load_config(path: str | Path | None = None) -> dict:
    """Lit et valide la configuration. Retourne un dict prêt à l'emploi :

    {"app", "profile", "display", "foods_build", "nutrients": [...], "references": {...}}
    """
    path = Path(path or os.environ.get("NUTRI_CONFIG") or DEFAULT_PATH)
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        raise ConfigError(f"Fichier de configuration introuvable : {path}") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path.name} : syntaxe TOML invalide ({e})") from None

    unknown = set(raw) - {"app", "profile", "display", "foods_build", "nutrients"}
    if unknown:
        raise ConfigError(f"Sections inconnues dans {path.name} : {sorted(unknown)}")

    app = _section(raw, "app", APP_DEFAULTS)
    profile = _section(raw, "profile", PROFILE_DEFAULTS)
    display = _section(raw, "display", DISPLAY_DEFAULTS)
    build = _section(raw, "foods_build", BUILD_DEFAULTS)

    _number(app["suggestions_max"], "[app] suggestions_max", minimum=1)
    age_min = _number(profile["age_min"], "[profile] age_min", minimum=0)
    age_max = _number(profile["age_max"], "[profile] age_max", minimum=1)
    if age_min >= age_max:
        raise ConfigError("[profile] age_min doit être inférieur à age_max")
    _number(profile["default_age"], "[profile] default_age", minimum=age_min)
    if profile["default_age"] > age_max:
        raise ConfigError("[profile] default_age doit être <= age_max")
    lo_hi = profile["menstruation_age_range"]
    if not (isinstance(lo_hi, list) and len(lo_hi) == 2 and lo_hi[0] <= lo_hi[1]):
        raise ConfigError("[profile] menstruation_age_range : [âge_min, âge_max] attendu")
    _number(display["ring_size"], "[display] ring_size", minimum=20)
    _number(display["ring_stroke_width"], "[display] ring_stroke_width", minimum=1)
    _number(build["below_limit_factor"], "[foods_build] below_limit_factor", minimum=0)
    _number(build["traces_value"], "[foods_build] traces_value", minimum=0)

    raw_nutrients = raw.get("nutrients")
    if not isinstance(raw_nutrients, dict) or not raw_nutrients:
        raise ConfigError("Aucun nutriment défini : ajoute au moins un bloc [nutrients.<clé>]")

    nutrients: list[dict] = []
    references: dict[str, dict] = {}
    seen_columns: dict[str, str] = {}
    for key, block in raw_nutrients.items():
        where = f"[nutrients.{key}]"
        if not isinstance(block, dict):
            raise ConfigError(f"{where} doit être une table")
        allowed = {"label", "unit", "group", "csv_column", "ciqual", "reference"}
        extra = set(block) - allowed
        if extra:
            raise ConfigError(f"{where} : clés inconnues {sorted(extra)} (autorisées : {sorted(allowed)})")
        for req in ("label", "unit", "group", "csv_column", "reference"):
            if req not in block:
                raise ConfigError(f"{where} : « {req} » manquant")
            if req != "reference" and not isinstance(block[req], str):
                raise ConfigError(f"{where} : « {req} » doit être un texte")
        if block["csv_column"] in seen_columns:
            raise ConfigError(
                f"{where} : la colonne « {block['csv_column']} » est déjà utilisée par {seen_columns[block['csv_column']]}"
            )
        seen_columns[block["csv_column"]] = key

        ref = block["reference"]
        if not isinstance(ref, dict):
            raise ConfigError(f"{where}.reference doit être une table")
        extra = set(ref) - set(BAND_KEYS) - set(SCALAR_KEYS)
        if extra:
            raise ConfigError(
                f"{where}.reference : clés inconnues {sorted(extra)} "
                f"(autorisées : {sorted(BAND_KEYS + SCALAR_KEYS)})"
            )
        for req in REQUIRED_BANDS:
            if req not in ref:
                raise ConfigError(f"{where}.reference : « {req} » manquant")
        parsed: dict = {}
        for bk in BAND_KEYS:
            if bk in ref:
                parsed[bk] = _bands(ref[bk], f"{where}.reference.{bk}", age_max)
        for sk in SCALAR_KEYS:
            if sk in ref:
                parsed[sk] = _number(ref[sk], f"{where}.reference.{sk}", minimum=0)
        references[key] = parsed

        nutrients.append(
            {
                "key": key,
                "label": block["label"],
                "unit": block["unit"],
                "group": block["group"],
                "col": block["csv_column"],
                "ciqual": _ciqual(block.get("ciqual", []), f"{where}.ciqual"),
            }
        )

    groups = {n["group"] for n in nutrients}
    if build["required_group"] and build["required_group"] not in groups:
        raise ConfigError(
            f"[foods_build] required_group = {build['required_group']!r} ne correspond à aucun groupe "
            f"de nutriments ({sorted(groups)})"
        )

    return {
        "app": app,
        "profile": profile,
        "display": display,
        "foods_build": build,
        "nutrients": nutrients,
        "references": references,
    }