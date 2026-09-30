"""Onglet « Semaine » : taux de complétion de chaque nutriment suivi, jour par jour, du lundi
au dimanche, avec la moyenne de la semaine. Les flèches du haut passent aux semaines
précédentes / suivantes ; on peut aussi faire glisser le tableau (vers la droite = semaine
précédente) : il suit le doigt, puis se cale sur une semaine entière, du lundi au dimanche
(ft.PageView, un défilement natif). Seuls les jours et les cases glissent : la colonne des
nutriments reste fixe à gauche, et ses moyennes se mettent à jour quand la semaine change.
Toucher une case remplie ouvre le détail du nutriment pour ce jour-là (ui/nutrient_detail.py),
comme un cercle de l'accueil. Toucher un jour (en-tête de colonne) ou une case vide « – » ouvre
l'accueil sur ce jour-là, pour ajouter ou modifier ses repas.

Les calculs sont dans history.py ; ce fichier ne fait que les afficher.
"""

from __future__ import annotations

import datetime
from typing import Callable

import flet as ft

from history import WeekSummary, browsable_weeks, week_summary
from nutrition import recommended_intakes, selected_nutrients

from .context import AppContext
from .dates import DAY_LETTERS, day_title, week_label
from .layout import screen_title, show_screen
from .nutrient_detail import show_nutrient_detail
from .style import COLOR_DONE, LOW_THRESHOLD, level_color
from .widgets import mouse_draggable

LABEL_WIDTH = 100  # colonne des noms de nutriments ; les 7 colonnes de jours se partagent le reste
CELL_HEIGHT = 34
CELL_SPACING = 4
HEADER_HEIGHT = 40  # ligne des jours
ROW_HEIGHT = 38  # une ligne de nutriment (nom + moyenne)
SUMMARY_HEIGHT = 24  # « 4 jours notés sur 7 »
MIN_WEEKS = 4  # semaines consultables au minimum, même sans historique
ARROW_ANIMATION_MS = 350  # glissement quand on utilise les flèches


def rate_of(day_rates: dict[str, float] | None, key: str) -> float | None:
    return None if day_rates is None else day_rates[key]


def rate_cell(ratio: float | None, future: bool, on_click: Callable[[], None] | None = None) -> ft.Control:
    """Une case du tableau : coche verte (apport atteint), sinon le pourcentage sur fond rouge (bas)
    ou orange (en cours), d'autant plus soutenu qu'on s'approche de 100 % ; « – » si rien n'a été
    noté, vide pour un jour à venir. Couleurs : ui/style.level_color. `on_click` : appelé quand on
    touche la case (jamais pour un jour à venir)."""
    clickable = on_click is not None and not future
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


def day_header(day: datetime.date, today: datetime.date, on_click: Callable[[], None] | None = None) -> ft.Control:
    """En-tête d'une colonne (« M 29 »). `on_click` : appelé quand on le touche (sauf jour à venir)."""
    clickable = on_click is not None and day <= today
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
        border_radius=8,
        ink=clickable,
        on_click=(lambda e: on_click()) if clickable else None,
        tooltip="Modifier les repas de ce jour" if clickable else None,
    )


def nutrient_label(label: str, average_text: ft.Text) -> ft.Control:
    """Nom d'un nutriment et sa moyenne, dans la colonne fixe de gauche. `average_text` est mis à
    jour par set_average à chaque changement de semaine."""
    return ft.Container(
        ft.Column([ft.Text(label, size=13, weight=ft.FontWeight.W_600), average_text], spacing=0),
        width=LABEL_WIDTH,
        height=ROW_HEIGHT,
        alignment=ft.Alignment.CENTER_LEFT,
    )


def set_average(text: ft.Text, average: float | None) -> None:
    text.value = "moy. –" if average is None else f"moy. {average * 100:.0f} %"
    text.color = COLOR_DONE if (average or 0) >= 1 else ft.Colors.GREY_700


def summary_text(summary: WeekSummary, shown: list[dict]) -> str:
    if not shown:
        return "Aucun nutriment suivi : choisis-en dans ton profil."
    n = summary.filled_days
    return f"{n} jour{'s' if n > 1 else ''} noté{'s' if n > 1 else ''} sur 7."


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
    summary: WeekSummary,
    shown: list[dict],
    today: datetime.date,
    on_cell_click: Callable[[dict, datetime.date], None],
    on_day_click: Callable[[datetime.date], None],
) -> ft.Control:
    """Une page du calendrier : la ligne des jours et une ligne de cases par nutriment (les noms et
    moyennes sont dans la colonne fixe, à gauche). Hauteur fixe : voir table_height.
    `on_cell_click(nutriment, jour)` : case remplie touchée ; `on_day_click(jour)` : en-tête d'un
    jour ou case vide touchée."""

    def cell_action(nutrient: dict, day: datetime.date) -> Callable[[], None]:
        if summary.rates[day] is None:  # rien de noté : on va directement noter ses repas
            return lambda: on_day_click(day)
        return lambda: on_cell_click(nutrient, day)

    header = ft.Row([day_header(d, today, lambda d=d: on_day_click(d)) for d in summary.days], spacing=CELL_SPACING)
    rows = [
        ft.Row(
            [
                rate_cell(
                    rate_of(summary.rates[d], n["key"]),
                    future=d > today,
                    on_click=cell_action(n, d),
                )
                for d in summary.days
            ],
            spacing=CELL_SPACING,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        for n in shown
    ]
    return ft.Column(
        [ft.Container(header, height=HEADER_HEIGHT), *[ft.Container(row, height=ROW_HEIGHT) for row in rows]],
        spacing=CELL_SPACING,
    )


def table_height(nutrient_count: int) -> int:
    """Hauteur du calendrier (le PageView a besoin d'une hauteur fixe)."""
    blocks = [HEADER_HEIGHT, *[ROW_HEIGHT] * nutrient_count]
    return sum(blocks) + CELL_SPACING * (len(blocks) - 1)


def show_week(ctx: AppContext) -> None:
    profile = ctx.get_profile()
    recommended = recommended_intakes(profile)
    shown = selected_nutrients(profile)
    today = datetime.date.today()
    starts = browsable_weeks(ctx.state["journal"], today, min_weeks=MIN_WEEKS)  # plus ancienne -> en cours
    height = table_height(len(shown))

    def open_day(day: datetime.date) -> None:
        """Toucher un jour : l'accueil s'ouvre sur ce jour, pour ajouter ou modifier ses repas."""
        ctx.router.show_main(day)

    def open_detail(nutrient: dict, day: datetime.date) -> None:
        """Toucher une case remplie : détail du nutriment ce jour-là, aliment par aliment."""
        label = None if day == today else day_title(day, today)
        show_nutrient_detail(
            ctx,
            nutrient,
            ctx.entries_for(day),
            recommended[nutrient["key"]],
            day_label=label,
            on_edit_day=lambda: open_day(day),
        )

    # Une page par semaine. Seules la semaine affichée et ses voisines sont construites (au fil des
    # glissements) : les autres restent des cadres vides de la bonne hauteur, pour rester léger même
    # avec des mois d'historique.
    pages = [ft.Container(height=height) for _ in starts]
    summaries: dict[int, WeekSummary] = {}  # calculées à la demande, une fois par semaine

    def summary_of(index: int) -> WeekSummary:
        if index not in summaries:
            keys = [n["key"] for n in shown]
            summaries[index] = week_summary(ctx.state["journal"], starts[index], ctx.foods, recommended, keys)
        return summaries[index]

    def build(index: int) -> None:
        if 0 <= index < len(pages) and pages[index].content is None:
            pages[index].content = week_table(summary_of(index), shown, today, open_detail, open_day)

    # Colonne fixe de gauche : les noms ne bougent pas, les moyennes suivent la semaine affichée.
    average_texts = {n["key"]: ft.Text(size=11) for n in shown}
    labels = ft.Column(
        [
            ft.Container(height=HEADER_HEIGHT),  # en face de la ligne des jours
            *[nutrient_label(n["label"], average_texts[n["key"]]) for n in shown],
        ],
        spacing=CELL_SPACING,
        width=LABEL_WIDTH,
    )
    week_info = ft.Text(color=ft.Colors.GREY_700)  # « 4 jours notés sur 7 »

    subtitle = ft.Text(color=ft.Colors.GREY_700)
    previous_button = ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Semaine précédente")
    next_button = ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Semaine suivante")

    def show_index(index: int) -> None:
        """Après un glissement (ou une flèche) : prépare les semaines voisines et met l'en-tête à jour."""
        for i in (index - 1, index, index + 1):
            build(i)
        summary = summary_of(index)
        subtitle.value = week_label(starts[index])
        for key, text in average_texts.items():
            set_average(text, summary.averages[key])
        week_info.value = summary_text(summary, shown)
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
                "Touche une case pour voir ce que chaque aliment a apporté, un jour pour modifier ses repas, "
                "et fais glisser le tableau vers la droite pour remonter dans le temps.",
                color=ft.Colors.GREY_700,
            ),
            # Seuls les jours et les cases glissent ; la colonne des nutriments reste en place.
            ft.Row(
                [labels, ft.Container(mouse_draggable(calendar), expand=True)],
                spacing=CELL_SPACING,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            week_info,
            ft.Divider(height=16),
            legend(),
        ],
        spacing=12,
    )
    show_index(len(starts) - 1)  # construit la semaine en cours et la précédente avant l'affichage
    show_screen(ctx, body, tab="semaine")
