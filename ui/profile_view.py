"""Fiche du profil (lecture seule) : qui tu es, et le repère journalier de chaque nutriment suivi,
groupe par groupe. Rien n'y est modifiable ; le bouton « Modifier » ouvre le formulaire, voir
ui/profile_edit.py.
"""

from __future__ import annotations

import flet as ft

from nutrition import GROUPS, NUTRIENTS, WOMAN_STATUSES, Profile, recommended_intakes, selected_nutrients

from .context import AppContext
from .layout import card, show_screen
from .widgets import group_icon, icon_badge, reference_label


def followed_count(count: int) -> str:
    """« 1 nutriment suivi », « 3 nutriments suivis »."""
    return f"{count} nutriment{'s' if count > 1 else ''} suivi{'s' if count > 1 else ''}"


def identity_card(profile: Profile) -> ft.Control:
    """« Femme · 30 ans » et, pour une femme, sa situation."""
    is_woman = profile.sex == "F"
    lines: list[ft.Control] = [
        ft.Text(f"{'Femme' if is_woman else 'Homme'} · {profile.age} ans", size=20, weight=ft.FontWeight.BOLD)
    ]
    if is_woman:
        lines.append(ft.Text(WOMAN_STATUSES[profile.effective_status()]["label"], color=ft.Colors.GREY_700))
    return card(
        ft.Row(
            [icon_badge(ft.Icons.WOMAN if is_woman else ft.Icons.MAN, size=56), ft.Column(lines, spacing=0)],
            spacing=16,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    )


def reference_row(nutrient: dict, reference: float | None) -> ft.Control:
    """« Fer ........ 15 mg » ; « 5 g max » pour un maximum, « sans repère » en gris sinon."""
    muted = nutrient["goal"] is None
    return ft.Row(
        [
            ft.Text(nutrient["label"], expand=True),
            ft.Text(
                reference_label(nutrient, reference),
                color=ft.Colors.GREY_500 if muted else None,
                weight=None if muted else ft.FontWeight.W_600,
            ),
        ],
        spacing=12,
    )


def group_card(group: dict, nutrients: list[dict], references: dict[str, float | None]) -> ft.Control:
    """Les nutriments suivis d'un groupe, avec leur repère du jour."""
    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        icon_badge(group_icon(group)),
                        ft.Column(
                            [
                                ft.Text(group["name"], size=16, weight=ft.FontWeight.W_600),
                                ft.Text(followed_count(len(nutrients)), size=12, color=ft.Colors.GREY_700),
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Column([reference_row(n, references[n["key"]]) for n in nutrients], spacing=8),
            ],
            spacing=14,
        )
    )


def show_profile(ctx: AppContext) -> None:
    current = Profile.from_dict(ctx.state["profile"])
    references = recommended_intakes(current)
    chosen = selected_nutrients(current)

    cards = [
        group_card(group, [n for n in chosen if n["group"] == group["name"]], references)
        for group in GROUPS
        if any(n["group"] == group["name"] for n in chosen)
    ]
    others = len(NUTRIENTS) - len(chosen)

    appbar = ft.AppBar(
        title=ft.Text("Ton profil", weight=ft.FontWeight.BOLD),
        center_title=False,
        leading=ft.IconButton(
            ft.Icons.ARROW_BACK, tooltip="Retour", on_click=lambda e: ctx.router.show_main(ctx.home_day)
        ),
        actions=[
            ft.FilledButton("Modifier", icon=ft.Icons.EDIT, on_click=lambda e: ctx.router.show_profile_edit()),
            ft.Container(width=12),
        ],
    )
    show_screen(
        ctx,
        ft.Column(
            [
                identity_card(current),
                ft.Container(height=4),
                ft.Text("Tes repères journaliers", size=18, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Calculés d'après ton profil. « max » : un maximum à ne pas dépasser ; « sans repère » : "
                    "l'app affiche seulement la quantité du jour.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                *cards,
                *(
                    [
                        ft.Text(
                            f"{others} autre{'s' if others > 1 else ''} nutriment{'s' if others > 1 else ''} "
                            "à suivre si tu veux : touche « Modifier ».",
                            size=12,
                            color=ft.Colors.GREY_700,
                        )
                    ]
                    if others
                    else []
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        appbar=appbar,
    )
