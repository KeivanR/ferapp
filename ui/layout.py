"""Mise en page commune à tous les écrans : show_screen() remplace le contenu de la page, et
show_popup() affiche une carte par-dessus, sur un fond flouté.

Chaque écran construit son contenu puis appelle show_screen(ctx, contenu, ...) au lieu de
manipuler la page lui-même. Ainsi, la barre du haut, la barre de navigation du bas et les
marges sont gérées au même endroit : un écran sans onglet (profil, ajout d'un aliment...)
retire automatiquement la barre du bas laissée par l'écran précédent.
"""

from __future__ import annotations

import asyncio
from typing import Callable

import flet as ft

from .context import AppContext
from .navigation import navigation_bar
from .style import CARD_SHADOW

PADDING = ft.Padding.only(left=16, right=16, top=8, bottom=24)  # marges d'un écran normal
CENTERED_PADDING = 30  # marges d'un écran centré (démarrage, bienvenue)
POPUP_BLUR = 8  # intensité du flou derrière une fenêtre show_popup
POPUP_WIDTH = 340  # tient sur un petit téléphone (360 px) avec les marges
POPUP_ANIMATION_MS = 250
POPUP_GROW_DELAY = 0.03  # s, laisse la carte s'afficher petite avant de l'agrandir
POPUP_TAG = "popup"  # marque les fenêtres show_popup dans page.overlay, pour les retrouver


def show_screen(
    ctx: AppContext,
    content: ft.Control,
    *,
    appbar: ft.AppBar | None = None,
    tab: str | None = None,
    centered: bool = False,
) -> None:
    """Affiche `content` comme nouvel écran.

    appbar   : barre du haut (None = aucune) ;
    tab      : clé de l'onglet (ui/navigation.TABS) si l'écran fait partie de la barre du bas,
               None pour un écran hors onglets (la barre du bas est alors masquée) ;
    centered : contenu centré dans toute la hauteur (écrans de démarrage et de bienvenue).
    """
    page = ctx.page
    close_popups(ctx)  # une fenêtre show_popup ne survit pas à un changement d'écran
    page.appbar = appbar
    page.navigation_bar = navigation_bar(ctx, tab) if tab else None
    page.clean()
    if centered:
        body = ft.Container(content, expand=True, alignment=ft.Alignment.CENTER, padding=CENTERED_PADDING)
    else:
        body = ft.Container(content, padding=PADDING)
    page.add(ft.SafeArea(body, expand=centered))


def screen_title(title: str, subtitle: str | None = None, trailing: ft.Control | None = None) -> ft.Control:
    """En-tête des écrans à onglet : grand titre, sous-titre gris facultatif, et un bouton
    facultatif aligné à droite (ex. accès au profil)."""
    texts: list[ft.Control] = [ft.Text(title, size=26, weight=ft.FontWeight.BOLD)]
    if subtitle:
        texts.append(ft.Text(subtitle, color=ft.Colors.GREY_700))
    return ft.Row(
        [ft.Column(texts, spacing=0, expand=True), *([trailing] if trailing else [])],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def show_popup(ctx: AppContext, content: ft.Control, *, width: int = POPUP_WIDTH) -> Callable[[], None]:
    """Affiche `content` dans une carte au centre de l'écran, qui s'agrandit en apparaissant,
    par-dessus la page floutée (barres du haut et du bas comprises). Toucher en dehors de la carte
    la ferme. Retourne la fonction qui la ferme (pour un bouton « Fermer » dans `content`).

    La barre du bas est masquée pendant ce temps : page.overlay ne la recouvre pas, elle resterait
    nette et cliquable par-dessus le flou."""
    page = ctx.page
    animation = ft.Animation(POPUP_ANIMATION_MS, ft.AnimationCurve.EASE_OUT_BACK)
    card = ft.Container(
        content,
        width=width,
        padding=20,
        border_radius=24,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
        shadow=CARD_SHADOW,
        scale=0.5,
        animate_scale=animation,
        on_click=lambda e: None,  # un toucher DANS la carte ne doit pas la fermer
    )
    backdrop = ft.Container(
        card,
        left=0,
        top=0,
        right=0,
        bottom=0,
        padding=16,
        alignment=ft.Alignment.CENTER,
        blur=ft.Blur(POPUP_BLUR, POPUP_BLUR),  # floute tout ce qui est derrière
        bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
        opacity=0,
        animate_opacity=POPUP_ANIMATION_MS,
        on_click=lambda e: close(),
        data=POPUP_TAG,
    )

    def close() -> None:
        if backdrop in page.overlay:
            close_popups(ctx)
            page.update()

    if page.navigation_bar:
        page.navigation_bar.visible = False
    page.overlay.append(backdrop)
    page.update()

    async def grow() -> None:
        # Une fois la petite carte affichée, on lui donne sa taille normale : Flet anime le passage.
        await asyncio.sleep(POPUP_GROW_DELAY)
        card.scale = 1
        backdrop.opacity = 1
        page.update()

    page.run_task(grow)
    return close


def close_popups(ctx: AppContext) -> None:
    """Ferme les fenêtres show_popup ouvertes et réaffiche la barre du bas (sans rafraîchir la page)."""
    page = ctx.page
    page.overlay[:] = [c for c in page.overlay if c.data != POPUP_TAG]
    if page.navigation_bar:
        page.navigation_bar.visible = True
