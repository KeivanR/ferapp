"""Page de démarrage : présente l'app quelques instants, puis oriente vers la page
principale (profil déjà rempli) ou une invitation à créer son profil (premier lancement).
"""

from __future__ import annotations

import asyncio

import flet as ft

from nutrition import CONFIG

from .context import AppContext


def show_splash(ctx: AppContext) -> None:
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
                        ft.Icon(ft.Icons.EGG_ALT_OUTLINED, size=72, color=ft.Colors.PRIMARY),
                        ft.Text(CONFIG["app"]["title"], size=28, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            CONFIG["app"]["tagline"],
                            color=ft.Colors.GREY_700,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=24),
                        ft.ProgressRing(width=28, height=28, stroke_width=3),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10,
                ),
            ),
            expand=True,
        )
    )

    async def go_next():
        await asyncio.sleep(CONFIG["app"]["splash_seconds"])
        if ctx.state.get("profile"):
            ctx.router.show_main()
        else:
            ctx.router.show_welcome()

    page.run_task(go_next)
