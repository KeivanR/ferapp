"""Écran de bienvenue : premier lancement, aucun profil enregistré. Invite à créer son
profil avant de proposer quoi que ce soit d'autre (voir show_splash, qui l'affiche
uniquement quand `ctx.state["profile"]` est vide).
"""

from __future__ import annotations

import flet as ft

from nutrition import CONFIG

from .context import AppContext


def show_welcome(ctx: AppContext) -> None:
    page = ctx.page
    page.appbar = None
    page.clean()
    page.add(
        ft.SafeArea(
            ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                padding=30,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.EGG_ALT_OUTLINED, size=64, color=ft.Colors.PRIMARY),
                        ft.Text(f"Bienvenue sur {CONFIG['app']['title']}", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Commence par renseigner ton profil (âge, sexe, nutriments à suivre) : "
                            "l'app calculera tes apports recommandés à partir de ce que tu manges.",
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=20),
                        ft.FilledButton(
                            "Remplir mon profil",
                            icon=ft.Icons.ARROW_FORWARD,
                            on_click=lambda e: ctx.router.show_profile_edit(),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
            ),
            expand=True,
        )
    )
