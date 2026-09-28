"""Barre de navigation du bas : la liste des onglets et la barre elle-même.

Les onglets sont décrits ici, en données, dans TABS : c'est le seul endroit à modifier pour en
ajouter, en retirer ou en réordonner un. Chaque onglet désigne l'écran à afficher par le nom
de son attribut dans le Router (ui/context.py), pas par un import : ce module ne connaît
aucun écran, il n'y a donc pas d'import circulaire.

Ajouter un onglet :
  1. crée l'écran ui/mon_ecran.py avec show_mon_ecran(ctx), qui appelle
     `show_screen(ctx, ..., tab="mon_onglet")` (ui/layout.py) ;
  2. ajoute `show_mon_ecran` au Router (ui/context.py) et branche-le dans ui/app.py ;
  3. ajoute une ligne Tab(...) ci-dessous.
"""

from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from .context import AppContext


@dataclass(frozen=True)
class Tab:
    key: str  # identifiant passé à show_screen(..., tab=key) par l'écran de l'onglet
    label: str
    icon: ft.IconData
    selected_icon: ft.IconData
    route: str  # nom de l'attribut du Router qui affiche l'écran, ex. "show_main"


TABS: list[Tab] = [
    Tab("accueil", "Accueil", ft.Icons.HOME_OUTLINED, ft.Icons.HOME, "show_main"),
    Tab("semaine", "Semaine", ft.Icons.CALENDAR_VIEW_WEEK_OUTLINED, ft.Icons.CALENDAR_VIEW_WEEK, "show_week"),
    Tab("ressources", "Ressources", ft.Icons.MENU_BOOK_OUTLINED, ft.Icons.MENU_BOOK, "show_resources"),
]


def tab_index(key: str) -> int:
    """Position de l'onglet `key` dans TABS (ValueError si inconnu : faute de frappe dans un écran)."""
    for i, tab in enumerate(TABS):
        if tab.key == key:
            return i
    raise ValueError(f"Onglet inconnu : {key!r} (onglets définis : {[t.key for t in TABS]})")


def navigation_bar(ctx: AppContext, current: str) -> ft.NavigationBar:
    """Barre du bas, avec l'onglet `current` sélectionné ; un clic affiche l'écran de l'onglet."""

    def on_change(e) -> None:
        tab = TABS[e.control.selected_index]
        if tab.key != current:
            getattr(ctx.router, tab.route)()

    return ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(icon=t.icon, selected_icon=t.selected_icon, label=t.label) for t in TABS
        ],
        selected_index=tab_index(current),
        on_change=on_change,
    )
