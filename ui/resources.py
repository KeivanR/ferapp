"""Onglet « Ressources » : liens utiles regroupés par rubrique, puis questions fréquentes.

Le contenu n'est pas écrit ici mais dans config/ressources.toml (modifiable sans toucher au
code) ; il est lu et vérifié une fois, au démarrage de l'app.
"""

from __future__ import annotations

import flet as ft

from config import load_resources

from .context import AppContext
from .layout import screen_title, show_screen

RESOURCES = load_resources()


def section_title(text: str) -> ft.Control:
    return ft.Text(text, size=18, weight=ft.FontWeight.W_600)


def link_tile(link: dict) -> ft.Control:
    """Un lien : un toucher l'ouvre dans le navigateur."""
    return ft.ListTile(
        title=ft.Text(link["title"]),
        subtitle=ft.Text(link["description"], size=12, color=ft.Colors.GREY_700) if link["description"] else None,
        trailing=ft.Icon(ft.Icons.OPEN_IN_NEW, size=18),
        url=link["url"],
        content_padding=ft.Padding.only(left=0, right=4),
    )


def links_by_group(links: list[dict]) -> list[ft.Control]:
    """Rubriques dans l'ordre de leur première apparition dans le fichier, liens dans l'ordre du fichier."""
    groups: dict[str, list[dict]] = {}
    for link in links:
        groups.setdefault(link["group"], []).append(link)
    controls: list[ft.Control] = []
    for group, group_links in groups.items():
        controls.append(ft.Text(group, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700))
        controls.extend(link_tile(link) for link in group_links)
    return controls


def faq_tile(item: dict) -> ft.Control:
    """Une question : un toucher déplie la réponse."""
    return ft.ExpansionTile(
        title=ft.Text(item["question"], weight=ft.FontWeight.W_500),
        controls=[ft.Text(item["answer"])],
        controls_padding=ft.Padding.only(left=16, right=16, bottom=12),
        tile_padding=ft.Padding.only(left=0, right=4),
        expanded_cross_axis_alignment=ft.CrossAxisAlignment.START,
    )


def show_resources(ctx: AppContext) -> None:
    show_screen(
        ctx,
        ft.Column(
            [
                screen_title("Ressources", "Pour aller plus loin, et les réponses aux questions courantes."),
                ft.Container(height=4),
                section_title("Liens utiles"),
                *links_by_group(RESOURCES["links"]),
                ft.Divider(height=24),
                section_title("Questions fréquentes"),
                ft.Column([faq_tile(item) for item in RESOURCES["faq"]], spacing=0),
                ft.Divider(height=24),
                ft.Text(
                    "Cette application aide à suivre ses apports ; elle ne remplace pas l'avis d'un médecin "
                    "ou d'un diététicien.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
            ],
            spacing=6,
        ),
        tab="ressources",
    )
