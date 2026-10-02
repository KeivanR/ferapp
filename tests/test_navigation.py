"""Cohérence de l'interface avec la configuration : chaque onglet pointe vers un écran existant,
chaque groupe de nutriments a une icône qui existe."""

import dataclasses

import pytest

from ui.context import Router
from ui.navigation import TABS, tab_index


def test_every_tab_points_to_a_router_screen():
    screens = {f.name for f in dataclasses.fields(Router)}
    for tab in TABS:
        assert tab.route in screens, f"onglet {tab.key!r} : {tab.route!r} n'existe pas dans Router"


def test_tab_keys_are_unique_and_found():
    keys = [tab.key for tab in TABS]
    assert len(keys) == len(set(keys))
    assert [tab_index(k) for k in keys] == list(range(len(TABS)))
    with pytest.raises(ValueError):
        tab_index("inexistant")


def test_every_nutrient_group_has_an_existing_icon():
    import flet as ft

    from nutrition import GROUPS

    for group in GROUPS:
        assert hasattr(ft.Icons, group["icon"]), f'[groups."{group["name"]}"] icon : {group["icon"]!r} inconnue'
