"""Cercles de complétion de l'onglet Accueil.

- nutrient_ring / rings_grid : un petit cercle par nutriment suivi, dans une grille qui passe à la
  ligne toute seule selon la largeur de l'écran (jamais de cercle coupé à droite). Toucher un
  cercle appelle `on_click(nutriment)` : l'accueil ouvre alors le détail (ui/nutrient_detail.py).
- segmented_ring : un grand cercle dont la barre de progression est découpée en segments de
  couleur (un par aliment), utilisé par ce détail.

Réglages : config.toml, [display] (tailles, couleurs).
"""

from __future__ import annotations

import math
from typing import Callable

import flet as ft
import flet.canvas as cv

from .style import COLOR_DONE, COLOR_TODO, RING_SIZE, RING_SIZE_MAX, RING_STROKE
from .widgets import fmt

GRID_SPACING = 12  # espace entre deux cercles, horizontalement et verticalement
MIN_RING_WIDTH = 120  # largeur minimale d'une case : « Vitamine B12 » tient sur une ligne, et 3 cases par ligne
LABEL_SIZE = 16  # nom du nutriment sous le cercle
AMOUNT_SIZE = 13  # quantité du jour / apport recommandé
TRACK_COLOR = ft.Colors.GREY_200  # fond (« rail ») des cercles
SEGMENT_GAP = 2  # espace (px) entre deux segments du grand cercle, pour bien les distinguer


def ring_size_for(count: int) -> int:
    """Diamètre des cercles selon le nombre de nutriments suivis : très grand (jusqu'à
    RING_SIZE_MAX) s'il y en a peu, jusqu'au minimum RING_SIZE s'il y en a beaucoup — pour
    qu'un profil avec un seul nutriment lui laisse toute la place."""
    if count <= 1:
        return RING_SIZE_MAX
    size = round(RING_SIZE_MAX / count**0.5)
    return max(RING_SIZE, min(size, RING_SIZE_MAX))


def stroke_for(size: int) -> int:
    """Épaisseur du trait : proportionnelle au diamètre, jamais sous RING_STROKE."""
    return max(RING_STROKE, round(RING_STROKE * size / RING_SIZE))


def ring_center(ratio: float, size: int, color: str) -> ft.Control:
    """Contenu du centre d'un cercle : une coche si l'apport est atteint, sinon le pourcentage."""
    if ratio >= 1:
        return ft.Icon(ft.Icons.CHECK, color=color, size=max(28, size // 4))
    return ft.Text(f"{ratio * 100:.0f}%", weight=ft.FontWeight.BOLD, size=max(16, size // 6))


def nutrient_ring(
    nutrient: dict,
    ratio: float,
    total: float,
    recommended: float,
    size: int,
    on_click: Callable[[dict], None] | None = None,
) -> ft.Control:
    """Un cercle de la grille : progression (orange, vert une fois l'apport atteint), pourcentage
    ou coche au centre, nom du nutriment et quantité du jour / apport recommandé."""
    color = COLOR_DONE if ratio >= 1 else COLOR_TODO
    stroke = stroke_for(size)
    ring = ft.Stack(
        [
            ft.ProgressRing(
                value=min(ratio, 1.0),
                stroke_width=stroke,
                width=size,
                height=size,
                color=color,
                bgcolor=TRACK_COLOR,
            ),
            ft.Container(ring_center(ratio, size, color), width=size, height=size, alignment=ft.Alignment.CENTER),
        ],
        width=size,
        height=size,
    )
    return ft.Container(
        ft.Column(
            [
                ring,
                ft.Container(height=stroke // 2),  # le trait déborde aussi sous le cercle
                ft.Text(nutrient["label"], weight=ft.FontWeight.W_600, size=LABEL_SIZE),
                ft.Text(
                    f"{fmt(total)} / {fmt(recommended)} {nutrient['unit']}",
                    size=AMOUNT_SIZE,
                    color=ft.Colors.GREY_700,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=3,
        ),
        width=max(MIN_RING_WIDTH, size + 24),
        # Le trait du cercle déborde de moitié autour de son carré : sans cette marge, le bord
        # arrondi de la case (qui découpe ce qui dépasse) rognerait le haut du cercle.
        padding=stroke // 2 + 4,
        border_radius=12,
        ink=on_click is not None,
        on_click=(lambda e: on_click(nutrient)) if on_click else None,
        tooltip="Voir le détail" if on_click else None,
    )


def rings_grid(
    nutrients: list[dict],
    ratios: dict[str, float],
    totals: dict[str, float],
    recommended: dict[str, float],
    on_click: Callable[[dict], None] | None = None,
) -> ft.Control:
    """La grille des cercles, centrée.

    Le Row(wrap=True) est placé dans un Container aligné (et non dans un autre Row) : il reçoit
    ainsi la largeur de l'écran comme limite et passe à la ligne au lieu de déborder à droite.
    """
    size = ring_size_for(len(nutrients))
    return ft.Container(
        ft.Row(
            [
                nutrient_ring(n, ratios[n["key"]], totals[n["key"]], recommended[n["key"]], size, on_click)
                for n in nutrients
            ],
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=GRID_SPACING,
            run_spacing=GRID_SPACING,
        ),
        alignment=ft.Alignment.TOP_CENTER,
    )


def segmented_ring(segments: list[tuple[float, str]], size: int, center: ft.Control | None = None) -> ft.Control:
    """Grand cercle dont la progression est une suite de segments colorés, dans l'ordre, en partant
    du haut et dans le sens des aiguilles d'une montre : `segments` = [(fraction du tour, couleur)].
    La somme des fractions (au plus 1) est la progression totale ; le reste du tour montre le rail."""
    stroke = stroke_for(size)
    inset = stroke / 2  # le trait est centré sur le cercle : on le rentre pour qu'il ne soit pas coupé
    box = {"x": inset, "y": inset, "width": size - stroke, "height": size - stroke}
    radius = (size - stroke) / 2
    gap = SEGMENT_GAP / radius if len(segments) > 1 else 0.0  # en radians

    def arc(start: float, sweep: float, color: str) -> cv.Arc:
        paint = ft.Paint(stroke_width=stroke, style=ft.PaintingStyle.STROKE, color=color)
        return cv.Arc(**box, start_angle=start, sweep_angle=sweep, use_center=False, paint=paint)

    shapes: list[cv.Shape] = [arc(0, 2 * math.pi, TRACK_COLOR)]
    start = -math.pi / 2  # midi
    for fraction, color in segments:
        sweep = 2 * math.pi * min(fraction, 1.0)
        if sweep > gap:
            shapes.append(arc(start + gap / 2, sweep - gap, color))
        start += sweep
    return ft.Stack(
        [
            cv.Canvas(shapes, width=size, height=size),
            ft.Container(center, width=size, height=size, alignment=ft.Alignment.CENTER),
        ],
        width=size,
        height=size,
    )