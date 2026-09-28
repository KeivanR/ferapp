"""Onglet « Semaine » : taux de complétion de chaque nutriment suivi, jour par jour, du lundi
au dimanche, avec la moyenne de la semaine. Les flèches du haut passent aux semaines
précédentes / suivantes.

Les calculs sont dans history.py ; ce fichier ne fait que les afficher.
"""

from __future__ import annotations

import datetime

import flet as ft

from history import DAYS_PER_WEEK, average_rates, rates_by_day, week_days, week_start
from nutrition import recommended_intakes, selected_nutrients

from .context import AppContext
from .layout import screen_title, show_screen
from .style import COLOR_DONE, LOW_THRESHOLD, level_color

DAY_LETTERS = ["L", "M", "M", "J", "V", "S", "D"]
MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip
LABEL_WIDTH = 100  # colonne des noms de nutriments ; les 7 colonnes de jours se partagent le reste
CELL_HEIGHT = 34
CELL_SPACING = 4


def week_label(start: datetime.date) -> str:
    """« du 21 au 27 septembre 2026 », « du 29 septembre au 5 octobre 2026 »..."""
    end = start + datetime.timedelta(days=DAYS_PER_WEEK - 1)
    if start.year != end.year:
        return f"du {start.day} {MONTHS[start.month - 1]} {start.year} au {end.day} {MONTHS[end.month - 1]} {end.year}"
    if start.month != end.month:
        return f"du {start.day} {MONTHS[start.month - 1]} au {end.day} {MONTHS[end.month - 1]} {end.year}"
    return f"du {start.day} au {end.day} {MONTHS[end.month - 1]} {end.year}"


def rate_of(day_rates: dict[str, float] | None, key: str) -> float | None:
    return None if day_rates is None else day_rates[key]


def rate_cell(ratio: float | None, future: bool) -> ft.Control:
    """Une case du tableau : coche verte (apport atteint), sinon le pourcentage sur fond rouge (bas)
    ou orange (en cours), d'autant plus soutenu qu'on s'approche de 100 % ; « – » si rien n'a été
    noté, vide pour un jour à venir. Couleurs : ui/style.level_color."""
    if future:
        content, bgcolor = None, None
    elif ratio is None:
        content, bgcolor = ft.Text("–", color=ft.Colors.GREY_600), ft.Colors.GREY_200
    elif ratio >= 1:
        content, bgcolor = ft.Icon(ft.Icons.CHECK, color=ft.Colors.WHITE, size=18), COLOR_DONE
    else:
        content = ft.Text(f"{ratio * 100:.0f}", size=12, weight=ft.FontWeight.W_600)
        bgcolor = ft.Colors.with_opacity(0.25 + 0.45 * ratio, level_color(ratio))
    return ft.Container(
        content,
        height=CELL_HEIGHT,
        expand=True,
        alignment=ft.Alignment.CENTER,
        border_radius=8,
        bgcolor=bgcolor,
    )


def day_header(day: datetime.date, today: datetime.date) -> ft.Control:
    is_today = day == today
    color = ft.Colors.PRIMARY if is_today else ft.Colors.GREY_700
    weight = ft.FontWeight.BOLD if is_today else None
    return ft.Container(
        ft.Column(
            [
                ft.Text(DAY_LETTERS[day.weekday()], color=color, weight=weight, size=12),
                ft.Text(str(day.day), color=color, weight=weight),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
        alignment=ft.Alignment.CENTER,
    )


def nutrient_label(label: str, average: float | None) -> ft.Control:
    avg_text = "moy. –" if average is None else f"moy. {average * 100:.0f} %"
    return ft.Container(
        ft.Column(
            [
                ft.Text(label, size=13, weight=ft.FontWeight.W_600),
                ft.Text(avg_text, size=11, color=COLOR_DONE if (average or 0) >= 1 else ft.Colors.GREY_700),
            ],
            spacing=0,
        ),
        width=LABEL_WIDTH,
    )


def legend() -> ft.Control:
    def item(cell: ft.Control, text: str) -> ft.Control:
        return ft.Row([ft.Container(cell, width=30), ft.Text(text, size=12, color=ft.Colors.GREY_700)], spacing=6)

    return ft.Column(
        [
            item(rate_cell(1.0, future=False), "apport recommandé atteint"),
            item(rate_cell(0.75, future=False), "% de l'apport recommandé (ici 75 %)"),
            item(rate_cell(0.3, future=False), f"apport bas : moins de {LOW_THRESHOLD * 100:.0f} %"),
            item(rate_cell(None, future=False), "rien noté ce jour-là"),
            ft.Text(
                "La moyenne ne compte que les jours où tu as noté quelque chose.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
        ],
        spacing=6,
    )


def show_week(ctx: AppContext) -> None:
    profile = ctx.get_profile()
    recommended = recommended_intakes(profile)
    shown = selected_nutrients(profile)
    today = datetime.date.today()
    displayed = {"start": week_start(today)}  # semaine affichée, modifiée par les flèches
    body = ft.Column(spacing=12)

    def change_week(weeks: int) -> None:
        displayed["start"] += datetime.timedelta(weeks=weeks)
        render()

    def render() -> None:
        start = displayed["start"]
        days = week_days(start)
        rates = rates_by_day(ctx.state["journal"], days, ctx.foods, recommended)
        averages = average_rates(rates, [n["key"] for n in shown])
        filled = sum(r is not None for r in rates.values())

        arrows = ft.Row(
            [
                ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Semaine précédente", on_click=lambda e: change_week(-1)),
                ft.IconButton(
                    ft.Icons.CHEVRON_RIGHT,
                    tooltip="Semaine suivante",
                    on_click=lambda e: change_week(1),
                    disabled=start >= week_start(today),  # pas de semaine future
                ),
            ],
            spacing=0,
        )
        table = ft.Column(
            [
                ft.Row(
                    [ft.Container(width=LABEL_WIDTH), *[day_header(d, today) for d in days]],
                    spacing=CELL_SPACING,
                ),
                *[
                    ft.Row(
                        [
                            nutrient_label(n["label"], averages[n["key"]]),
                            *[rate_cell(rate_of(rates[d], n["key"]), future=d > today) for d in days],
                        ],
                        spacing=CELL_SPACING,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                    for n in shown
                ],
            ],
            spacing=CELL_SPACING,
        )
        summary = (
            "Aucun nutriment suivi : choisis-en dans ton profil."
            if not shown
            else f"{filled} jour{'s' if filled > 1 else ''} noté{'s' if filled > 1 else ''} sur 7."
        )
        body.controls = [
            screen_title("Semaine", week_label(start), trailing=arrows),
            ft.Text(
                "Part de l'apport recommandé atteinte chaque jour, pour chaque nutriment suivi.",
                color=ft.Colors.GREY_700,
            ),
            table,
            ft.Text(summary, color=ft.Colors.GREY_700),
            ft.Divider(height=16),
            legend(),
        ]
        ctx.page.update()

    show_screen(ctx, body, tab="semaine")
    render()
