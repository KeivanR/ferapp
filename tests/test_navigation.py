"""Cohérence de la barre de navigation : chaque onglet pointe vers un écran existant."""

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
