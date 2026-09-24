"""Fiche du profil (lecture seule) : qui tu es et l'apport recommandé de chaque nutriment
suivi. Rien n'y est modifiable ; le bouton « Modifier » ouvre le formulaire, voir
ui/profile_edit.py.
"""

from __future__ import annotations

import flet as ft

from nutrition import WOMAN_STATUSES, Profile, recommended_intakes, selected_nutrients

from .context import AppContext
from .widgets import fmt


def show_profile(ctx: AppContext) -> None:
    page = ctx.page
    current = Profile.from_dict(ctx.state["profile"])
    recs = recommended_intakes(current)
    chosen = selected_nutrients(current)

    info_lines = [f"Âge : {current.age} ans", "Sexe : " + ("Femme" if current.sex == "F" else "Homme")]
    if current.sex == "F":
        info_lines.append("Situation : " + WOMAN_STATUSES[current.effective_status()]["label"])

    nutrient_rows = ft.Column(spacing=2)
    last_group = None
    for n in chosen:
        if n["group"] != last_group:
            last_group = n["group"]
            nutrient_rows.controls.append(
                ft.Text(last_group, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700)
            )
        nutrient_rows.controls.append(ft.Text(f"{n['label']} : {fmt(recs[n['key']])} {n['unit']} / jour"))
    if not chosen:
        nutrient_rows.controls.append(ft.Text("Aucun nutriment suivi.", color=ft.Colors.GREY_700))

    page.appbar = ft.AppBar(
        title=ft.Text("Ton profil", weight=ft.FontWeight.BOLD),
        center_title=False,
        leading=ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Retour", on_click=lambda e: ctx.router.show_main()),
        actions=[
            ft.FilledButton("Modifier", icon=ft.Icons.EDIT, on_click=lambda e: ctx.router.show_profile_edit()),
            ft.Container(width=12),
        ],
    )
    page.clean()
    page.add(
        ft.SafeArea(
            ft.Container(
                padding=ft.Padding.only(left=20, right=20, top=4, bottom=20),
                content=ft.Column(
                    [
                        *[ft.Text(line) for line in info_lines],
                        ft.Divider(height=20),
                        ft.Text("Apports recommandés", size=18, weight=ft.FontWeight.W_600),
                        nutrient_rows,
                    ],
                    spacing=6,
                ),
            )
        )
    )
