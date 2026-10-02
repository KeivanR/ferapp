"""Cercles de complétion de l'onglet Accueil.

- nutrient_ring / rings_grid : un petit cercle par nutriment suivi. Peu de nutriments : une grille
  centrée qui passe à la ligne selon la largeur de l'écran. Beaucoup (plus que RINGS_PER_ROW x
  ring_rows_max) : une bande de ring_rows_max lignes qui défile horizontalement, pour que les
  cercles ne repoussent pas le repas du jour hors de l'écran. Toucher un cercle appelle
  `on_click(nutriment)` : l'accueil ouvre alors le détail (ui/nutrient_detail.py).
- segmented_ring : un grand cercle dont la barre de progression est découpée en segments de
  couleur (un par aliment), utilisé par ce détail.

Réglages : config.toml, [display] (tailles, couleurs).
"""

from __future__ import annotations

import math
from typing import Callable

import flet as ft
import flet.canvas as cv

from nutrition import STATUS_DONE, STATUS_INFO, STATUS_OVER, intake_ratio, intake_status

from .style import RING_ROWS_MAX, RING_SIZE, RING_SIZE_MAX, RING_STROKE, status_color
from .widgets import fmt, reference_label

GRID_SPACING = 8  # espace entre deux cercles, horizontalement et verticalement
STRIP_ROW_SPACING = 4  # espace entre les lignes de la bande qui défile (plus serrée que la grille)
RINGS_PER_ROW = 3  # cercles par ligne sur un téléphone : sert à choisir entre grille et bande
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


def ring_center(status: str, ratio: float | None, amount: float, size: int, color: str) -> ft.Control:
    """Contenu du centre d'un cercle : une coche si l'apport à atteindre l'est ; le pourcentage du
    repère sinon (en rouge si un maximum est dépassé) ; la quantité seule quand un pourcentage n'a
    pas de sens (nutriment sans repère, ou maximum nul)."""
    if status == STATUS_DONE:
        return ft.Icon(ft.Icons.CHECK, color=color, size=max(28, size // 4))
    text = fmt(amount) if ratio is None else f"{ratio * 100:.0f}%"
    return ft.Text(
        text,
        weight=ft.FontWeight.BOLD,
        size=max(16, size // 6),
        color=color if status == STATUS_OVER else None,
    )


def ring_caption(nutrient: dict, status: str, amount: float, reference: float | None) -> str:
    """Ligne sous le nom : « 1.5 / 15 mg », « 3 / 5 g max », ou « g · sans repère » (la quantité
    est alors déjà au centre du cercle)."""
    if status == STATUS_INFO:
        return f"{nutrient['unit']} · sans repère"
    return f"{fmt(amount)} / {reference_label(nutrient, reference)}"


def nutrient_ring(
    nutrient: dict,
    amount: float,
    reference: float | None,
    size: int,
    on_click: Callable[[dict], None] | None = None,
) -> ft.Control:
    """Un cercle de la grille, selon le repère du nutriment (nutrition.intake_status) :
    - apport à atteindre : la progression, orange puis verte avec une coche une fois atteint ;
    - maximum à ne pas dépasser : la part du maximum déjà consommée, puis tout rouge au-delà ;
    - sans repère : un cercle vide avec la quantité du jour au centre."""
    status = intake_status(nutrient, amount, reference)
    ratio = intake_ratio(amount, reference)
    color = status_color(status)
    filled = 1.0 if status == STATUS_OVER else min(ratio or 0.0, 1.0)
    stroke = stroke_for(size)
    ring = ft.Stack(
        [
            ft.ProgressRing(
                value=filled,
                stroke_width=stroke,
                width=size,
                height=size,
                color=color,
                bgcolor=TRACK_COLOR,
            ),
            ft.Container(
                ring_center(status, ratio, amount, size, color), width=size, height=size, alignment=ft.Alignment.CENTER
            ),
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
                ft.Text(ring_caption(nutrient, status, amount, reference), size=AMOUNT_SIZE, color=ft.Colors.GREY_700),
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
    totals: dict[str, float],
    recommended: dict[str, float | None],
    on_click: Callable[[dict], None] | None = None,
) -> ft.Control:
    """Les cercles de l'accueil : grille centrée s'ils tiennent sur RING_ROWS_MAX lignes, sinon bande
    qui défile horizontalement (rings_strip)."""
    size = ring_size_for(len(nutrients))
    rings = [nutrient_ring(n, totals[n["key"]], recommended[n["key"]], size, on_click) for n in nutrients]
    if len(rings) > RINGS_PER_ROW * RING_ROWS_MAX:
        return rings_strip(rings, RING_ROWS_MAX)
    # Le Row(wrap=True) est placé dans un Container aligné (et non dans un autre Row) : il reçoit
    # ainsi la largeur de l'écran comme limite et passe à la ligne au lieu de déborder à droite.
    return ft.Container(
        ft.Row(
            rings,
            wrap=True,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=GRID_SPACING,
            run_spacing=GRID_SPACING,
        ),
        alignment=ft.Alignment.TOP_CENTER,
    )


def rings_strip(rings: list[ft.Control], rows: int) -> ft.Control:
    """Bande de `rows` lignes qui défile horizontalement. Les cercles sont rangés colonne par
    colonne (1 et 2 dans la première colonne, 3 et 4 dans la deuxième...) : les premiers
    nutriments de la liste sont donc tous visibles sans faire défiler. La colonne coupée au bord
    droit, et une ligne d'aide dessous, montrent qu'il y en a d'autres."""
    columns = [ft.Column(rings[i : i + rows], spacing=STRIP_ROW_SPACING) for i in range(0, len(rings), rows)]
    return ft.Column(
        [
            ft.Row(
                columns,
                scroll=ft.ScrollMode.AUTO,
                spacing=GRID_SPACING,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            ft.Row(
                [
                    ft.Text("Fais glisser pour voir tous les nutriments", size=12, color=ft.Colors.GREY_600),
                    ft.Icon(ft.Icons.SWIPE_LEFT_OUTLINED, size=16, color=ft.Colors.GREY_600),
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=4,
            ),
        ],
        spacing=2,
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
