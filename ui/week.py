"""Onglet « Semaine » : taux de complétion de chaque nutriment suivi, jour par jour, du lundi
au dimanche, avec la moyenne de la semaine. Les flèches du haut passent aux semaines
précédentes / suivantes ; on peut aussi faire glisser le tableau (vers la droite = semaine
précédente) : il suit le doigt, puis se cale sur une semaine entière, du lundi au dimanche
(ft.PageView, un défilement natif). Chaque page contient sa propre semaine, moyennes comprises.
Toucher une case remplie ouvre le détail du nutriment pour ce jour-là (ui/nutrient_detail.py),
comme un cercle de l'accueil.

Les calculs sont dans history.py ; ce fichier ne fait que les afficher.
"""

from __future__ import annotations

import datetime
from typing import Callable

import flet as ft

from history import DAYS_PER_WEEK, average_rates, browsable_weeks, rates_by_day, week_days
from nutrition import recommended_intakes, selected_nutrients

from .context import AppContext
from .layout import screen_title, show_screen
from .nutrient_detail import show_nutrient_detail
from .style import COLOR_DONE, LOW_THRESHOLD, level_color
from .widgets import mouse_draggable

DAY_LETTERS = ["L", "M", "M", "J", "V", "S", "D"]
DAY_NAMES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip
LABEL_WIDTH = 100  # colonne des noms de nutriments ; les 7 colonnes de jours se partagent le reste
CELL_HEIGHT = 34
CELL_SPACING = 4
HEADER_HEIGHT = 40  # ligne des jours
ROW_HEIGHT = 38  # une ligne de nutriment (nom + moyenne)
SUMMARY_HEIGHT = 24  # « 4 jours notés sur 7 »
MIN_WEEKS = 4  # semaines consultables au minimum, même sans historique
ARROW_ANIMATION_MS = 350  # glissement quand on utilise les flèches


def week_label(start: datetime.date) -> str:
    """« du 21 au 27 septembre 2026 », « du 29 septembre au 5 octobre 2026 »..."""
    end = start + datetime.timedelta(days=DAYS_PER_WEEK - 1)
    if start.year != end.year:
        return f"du {start.day} {MONTHS[start.month - 1]} {start.year} au {end.day} {MONTHS[end.month - 1]} {end.year}"
    if start.month != end.month:
        return f"du {start.day} {MONTHS[start.month - 1]} au {end.day} {MONTHS[end.month - 1]} {end.year}"
    return f"du {start.day} au {end.day} {MONTHS[end.month - 1]} {end.year}"


def day_label(day: datetime.date, today: datetime.date) -> str:
    """« aujourd'hui », « hier », sinon « mardi 23 septembre »."""
    if day == today:
        return "aujourd'hui"
    if day == today - datetime.timedelta(days=1):
        return "hier"
    return f"{DAY_NAMES[day.weekday()]} {day.day} {MONTHS[day.month - 1]}"


def rate_of(day_rates: dict[str, float] | None, key: str) -> float | None:
    return None if day_rates is None else day_rates[key]


def rate_cell(ratio: float | None, future: bool, on_click: Callable[[], None] | None = None) -> ft.Control:
    """Une case du tableau : coche verte (apport atteint), sinon le pourcentage sur fond rouge (bas)
    ou orange (en cours), d'autant plus soutenu qu'on s'approche de 100 % ; « – » si rien n'a été
    noté, vide pour un jour à venir. Couleurs : ui/style.level_color. `on_click` : appelé quand on
    touche la case (seulement pour un jour où quelque chose a été noté)."""
    clickable = on_click is not None and ratio is not None and not future
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
        ink=clickable,
        on_click=(lambda e: on_click()) if clickable else None,
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


def week_table(
    start: datetime.date,
    ctx: AppContext,
    shown: list[dict],
    recommended: dict[str, float],
    today: datetime.date,
    on_cell_click: Callable[[dict, datetime.date], None],
) -> ft.Control:
    """Le tableau d'une semaine (une page du calendrier) : en-tête des jours, une ligne par nutriment
    avec sa moyenne, et le nombre de jours notés. Hauteur fixe : voir table_height."""
    days = week_days(start)
    rates = rates_by_day(ctx.state["journal"], days, ctx.foods, recommended)
    averages = average_rates(rates, [n["key"] for n in shown])
    filled = sum(r is not None for r in rates.values())
    summary = (
        "Aucun nutriment suivi : choisis-en dans ton profil."
        if not shown
        else f"{filled} jour{'s' if filled > 1 else ''} noté{'s' if filled > 1 else ''} sur 7."
    )
    header = ft.Row([ft.Container(width=LABEL_WIDTH), *[day_header(d, today) for d in days]], spacing=CELL_SPACING)
    rows = [
        ft.Row(
            [
                nutrient_label(n["label"], averages[n["key"]]),
                *[
                    rate_cell(
                        rate_of(rates[d], n["key"]),
                        future=d > today,
                        on_click=lambda n=n, d=d: on_cell_click(n, d),
                    )
                    for d in days
                ],
            ],
            spacing=CELL_SPACING,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        for n in shown
    ]
    return ft.Column(
        [
            ft.Container(header, height=HEADER_HEIGHT),
            *[ft.Container(row, height=ROW_HEIGHT) for row in rows],
            ft.Container(
                ft.Text(summary, color=ft.Colors.GREY_700), height=SUMMARY_HEIGHT, alignment=ft.Alignment.CENTER_LEFT
            ),
        ],
        spacing=CELL_SPACING,
    )


def table_height(nutrient_count: int) -> int:
    """Hauteur d'une page du calendrier (le PageView a besoin d'une hauteur fixe)."""
    blocks = [HEADER_HEIGHT, *[ROW_HEIGHT] * nutrient_count, SUMMARY_HEIGHT]
    return sum(blocks) + CELL_SPACING * (len(blocks) - 1)


def show_week(ctx: AppContext) -> None:
    profile = ctx.get_profile()
    recommended = recommended_intakes(profile)
    shown = selected_nutrients(profile)
    today = datetime.date.today()
    starts = browsable_weeks(ctx.state["journal"], today, min_weeks=MIN_WEEKS)  # plus ancienne -> en cours
    height = table_height(len(shown))

    def open_detail(nutrient: dict, day: datetime.date) -> None:
        """Toucher une case : détail du nutriment ce jour-là, aliment par aliment."""
        entries = ctx.state["journal"].get(day.isoformat(), [])
        label = None if day == today else day_label(day, today)
        show_nutrient_detail(ctx, nutrient, entries, recommended[nutrient["key"]], day_label=label)

    # Une page par semaine. Seules la semaine affichée et ses voisines sont construites (au fil des
    # glissements) : les autres restent des cadres vides de la bonne hauteur, pour rester léger même
    # avec des mois d'historique.
    pages = [ft.Container(height=height) for _ in starts]

    def build(index: int) -> None:
        if 0 <= index < len(pages) and pages[index].content is None:
            pages[index].content = week_table(starts[index], ctx, shown, recommended, today, open_detail)

    subtitle = ft.Text(color=ft.Colors.GREY_700)
    previous_button = ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Semaine précédente")
    next_button = ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Semaine suivante")

    def show_index(index: int) -> None:
        """Après un glissement (ou une flèche) : prépare les semaines voisines et met l'en-tête à jour."""
        for i in (index - 1, index, index + 1):
            build(i)
        subtitle.value = week_label(starts[index])
        previous_button.disabled = index == 0
        next_button.disabled = index == len(starts) - 1  # pas de semaine future
        ctx.page.update()

    calendar = ft.PageView(
        pages,
        selected_index=len(starts) - 1,  # la semaine en cours, tout à droite
        height=height,
        on_change=lambda e: show_index(calendar.selected_index),
    )

    async def go(delta: int) -> None:
        index = calendar.selected_index + delta
        if 0 <= index < len(starts):
            await calendar.go_to_page(
                index, animation_duration=ARROW_ANIMATION_MS, animation_curve=ft.AnimationCurve.EASE_IN_OUT
            )

    async def on_previous(e) -> None:
        await go(-1)

    async def on_next(e) -> None:
        await go(1)

    previous_button.on_click = on_previous
    next_button.on_click = on_next

    body = ft.Column(
        [
            screen_title("Semaine", subtitle, trailing=ft.Row([previous_button, next_button], spacing=0)),
            ft.Text(
                "Part de l'apport recommandé atteinte chaque jour, pour chaque nutriment suivi. "
                "Touche une case pour voir ce que chaque aliment a apporté, "
                "fais glisser le tableau vers la droite pour remonter dans le temps.",
                color=ft.Colors.GREY_700,
            ),
            mouse_draggable(calendar),
            ft.Divider(height=16),
            legend(),
        ],
        spacing=12,
    )
    show_index(len(starts) - 1)  # construit la semaine en cours et la précédente avant l'affichage
    show_screen(ctx, body, tab="semaine")
