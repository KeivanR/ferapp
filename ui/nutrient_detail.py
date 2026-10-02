"""Détail d'un nutriment pour une journée, ouvert en touchant son cercle sur l'accueil (le jour
même) ou une case de l'onglet Semaine (le jour de la colonne) : le cercle s'affiche en
grand, par-dessus la page floutée, et sa barre de progression est découpée en segments de
couleur, un par aliment du jour, proportionnels à ce que chacun apporte. La liste en dessous
donne, pour chaque couleur, l'aliment et sa quantité. Depuis l'onglet Semaine, un bouton
permet d'aller modifier les repas de ce jour-là.

Les calculs viennent de nutrition.food_contributions ; les couleurs de config.toml ([display],
chart_colors).
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from nutrition import GOAL_MAX, STATUS_DONE, STATUS_INFO, STATUS_OVER, food_contributions, intake_ratio, intake_status

from .context import AppContext
from .layout import show_popup
from .rings import segmented_ring
from .style import CHART_COLOR_OTHER, CHART_COLORS, status_color
from .widgets import fmt, reference_label

BIG_RING_SIZE = 200


def show_nutrient_detail(
    ctx: AppContext,
    nutrient: dict,
    entries: list[dict],
    recommended: float | None,
    day_label: str | None = None,
    on_edit_day: Callable[[], None] | None = None,
) -> None:
    """`entries` : les entrées du journal de la journée ; `day_label` : la journée, affichée sous le
    titre (ex. « Mardi 23 septembre ») — rien pour aujourd'hui ; `on_edit_day` : si fourni, un
    bouton « Modifier les repas de ce jour » l'appelle."""
    items = food_contributions(entries, ctx.foods, nutrient["key"], max_foods=len(CHART_COLORS))
    colors = [CHART_COLOR_OTHER if item["other"] else CHART_COLORS[i] for i, item in enumerate(items)]
    total = sum(item["amount"] for item in items)
    status = intake_status(nutrient, total, recommended)
    ratio = intake_ratio(total, recommended)  # None : pas de repère (ou maximum nul)
    unit = nutrient["unit"]

    # Chaque aliment occupe sa part de la progression ; au-delà de 100 %, ou sans repère, le tour
    # complet est partagé entre les aliments, dans les mêmes proportions.
    filled = 1.0 if ratio is None else min(ratio, 1.0)
    segments = [(filled * item["amount"] / total, color) for item, color in zip(items, colors)] if total else []

    if status == STATUS_DONE:
        headline: ft.Control = ft.Icon(ft.Icons.CHECK, color=status_color(status), size=40)
    else:
        headline = ft.Text(
            fmt(total) if ratio is None else f"{ratio * 100:.0f}%",
            size=34,
            weight=ft.FontWeight.BOLD,
            color=status_color(status) if status == STATUS_OVER else None,
        )
    if status == STATUS_INFO:
        under = f"{unit} · sans repère"
    else:
        under = f"{fmt(total)} / {reference_label(nutrient, recommended)}"
    center = ft.Column(
        [
            headline,
            ft.Text(under, size=13, color=ft.Colors.GREY_700),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=2,
        tight=True,
    )

    def legend_row(item: dict, color: str) -> ft.Control:
        # Part du repère ; sans repère, part du total du jour.
        share = item["amount"] / (recommended or total)
        return ft.Row(
            [
                ft.Container(width=14, height=14, border_radius=4, bgcolor=color),
                ft.Text(item["food"], size=13, expand=True, italic=item["other"]),
                ft.Text(f"{fmt(item['amount'])} {unit} · {share * 100:.0f} %", size=13, color=ft.Colors.GREY_700),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    if items:
        legend = ft.Column([legend_row(item, color) for item, color in zip(items, colors)], spacing=8)
        caption = "Part de chaque aliment dans l'apport du jour " + (
            "(% = part du total du jour)."
            if ratio is None
            else "(% = part du maximum)."
            if nutrient["goal"] == GOAL_MAX
            else "(% = part de l'apport recommandé)."
        )
    else:
        when = "ce jour-là" if day_label else "aujourd'hui"
        legend = ft.Text(f"Aucun aliment noté {when} n'en apporte.", color=ft.Colors.GREY_700)
        caption = None

    close = None  # défini juste après show_popup, utilisé par le bouton ×

    def edit_day(e) -> None:
        close()
        on_edit_day()

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(nutrient["label"], size=22, weight=ft.FontWeight.BOLD),
                            *([ft.Text(day_label, color=ft.Colors.GREY_700)] if day_label else []),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.IconButton(ft.Icons.CLOSE, tooltip="Fermer", on_click=lambda e: close()),
                ],
            ),
            ft.Container(segmented_ring(segments, BIG_RING_SIZE, center), alignment=ft.Alignment.CENTER),
            ft.Container(height=4),
            *([ft.Text(caption, size=12, color=ft.Colors.GREY_700)] if caption else []),
            legend,
            *(
                [
                    ft.Container(
                        ft.TextButton("Modifier les repas de ce jour", icon=ft.Icons.EDIT_CALENDAR, on_click=edit_day),
                        alignment=ft.Alignment.CENTER,
                    )
                ]
                if on_edit_day
                else []
            ),
        ],
        spacing=10,
        tight=True,
    )
    close = show_popup(ctx, content)
