"""Détail d'un nutriment, ouvert en touchant son cercle sur l'accueil : le cercle s'affiche en
grand, par-dessus la page floutée, et sa barre de progression est découpée en segments de
couleur, un par aliment du jour, proportionnels à ce que chacun apporte. La liste en dessous
donne, pour chaque couleur, l'aliment et sa quantité.

Les calculs viennent de nutrition.food_contributions ; les couleurs de config.toml ([display],
chart_colors).
"""

from __future__ import annotations

import flet as ft

from nutrition import food_contributions

from .context import AppContext
from .layout import show_popup
from .rings import segmented_ring
from .style import CHART_COLOR_OTHER, CHART_COLORS, COLOR_DONE
from .widgets import fmt

BIG_RING_SIZE = 200


def show_nutrient_detail(ctx: AppContext, nutrient: dict, entries: list[dict], recommended: float) -> None:
    items = food_contributions(entries, ctx.foods, nutrient["key"], max_foods=len(CHART_COLORS))
    colors = [CHART_COLOR_OTHER if item["other"] else CHART_COLORS[i] for i, item in enumerate(items)]
    total = sum(item["amount"] for item in items)
    ratio = total / recommended if recommended else 0.0
    unit = nutrient["unit"]

    # Chaque aliment occupe sa part de la progression ; au-delà de 100 %, le tour complet est
    # partagé entre les aliments, dans les mêmes proportions.
    filled = min(ratio, 1.0)
    segments = [(filled * item["amount"] / total, color) for item, color in zip(items, colors)] if total else []

    center = ft.Column(
        [
            (
                ft.Icon(ft.Icons.CHECK, color=COLOR_DONE, size=40)
                if ratio >= 1
                else ft.Text(f"{ratio * 100:.0f}%", size=34, weight=ft.FontWeight.BOLD)
            ),
            ft.Text(f"{fmt(total)} / {fmt(recommended)} {unit}", size=13, color=ft.Colors.GREY_700),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=2,
        tight=True,
    )

    def legend_row(item: dict, color: str) -> ft.Control:
        share = item["amount"] / recommended if recommended else 0.0
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
        caption = "Part de chaque aliment dans l'apport du jour (% = part de l'apport recommandé)."
    else:
        legend = ft.Text("Aucun aliment noté aujourd'hui n'en apporte.", color=ft.Colors.GREY_700)
        caption = None

    close = None  # défini juste après show_popup, utilisé par le bouton ×
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(nutrient["label"], size=22, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, tooltip="Fermer", on_click=lambda e: close()),
                ],
            ),
            ft.Container(segmented_ring(segments, BIG_RING_SIZE, center), alignment=ft.Alignment.CENTER),
            ft.Container(height=4),
            *([ft.Text(caption, size=12, color=ft.Colors.GREY_700)] if caption else []),
            legend,
        ],
        spacing=10,
        tight=True,
    )
    close = show_popup(ctx, content)
