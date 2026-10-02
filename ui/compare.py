"""Onglet « Comparer » : on cherche un ou plusieurs aliments, et on voit ce qu'une même quantité de
chacun apporte pour chaque nutriment suivi, sous forme de barres horizontales.

  - une carte par nutriment, une barre par aliment : la longueur est la part de l'apport
    journalier recommandé (la même échelle pour toutes les cartes, donc comparable d'un
    nutriment à l'autre) ; un trait vertical marque 100 % quand l'échelle le dépasse ;
  - chaque aliment a une couleur et une lettre (A, B, C...), rappelées devant chaque barre : on
    s'y retrouve sans remonter à la liste, et sans dépendre de la seule couleur ;
  - la quantité comparée est 100 g, ou la portion habituelle de chaque aliment (son unité
    familière, ex. 1 fruit) : un bouton bascule de l'une à l'autre.

Les calculs sont dans comparison.py ; les réglages (nombre d'aliments, échelle, couleurs) dans
config/config.toml.
"""

from __future__ import annotations

import flet as ft

from comparison import (
    add_food,
    axis_max,
    best_slots,
    compared_grams,
    frequent_foods,
    is_selected,
    nutrient_shares,
    portion_for,
    remove_food,
    slot_letter,
    valid_selection,
)
from nutrition import find_food, recommended_intakes, search_foods, selected_nutrients

from .context import AppContext
from .layout import screen_title, show_screen
from .style import CHART_COLORS, COMPARE_MAX_FOODS, COMPARE_SCALE_MAX, COMPARE_SUGGESTIONS
from .widgets import fmt, make_food_input

BAR_HEIGHT = 12
BAR_RADIUS = 4  # bout arrondi de la barre (côté valeur) ; la base reste droite
BAR_UNITS = 1000  # précision de la longueur d'une barre (1/1000 de la largeur)
BAR_MIN_UNITS = 8  # un apport non nul reste visible, même très petit
BADGE_SIZE = 18
VALUE_WIDTH = 116  # colonne « 3.3 mg · 22 % » à droite des barres
ROW_SPACING = 8
CHIP_NAME_MAX = 30  # caractères affichés dans un raccourci « souvent noté »
MUTED = ft.Colors.GREY_700
REFERENCE_LINE_COLOR = ft.Colors.GREY_600


def ink_on(color: str) -> str:
    """Encre lisible sur un fond `color` (« #rrggbb ») : noire sur une couleur claire, blanche sinon."""
    r, g, b = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return ft.Colors.BLACK if 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45 else ft.Colors.WHITE


def badge(slot: int) -> ft.Control:
    """Pastille de l'aliment : sa couleur et sa lettre."""
    color = CHART_COLORS[slot]
    return ft.Container(
        ft.Text(slot_letter(slot), size=11, weight=ft.FontWeight.BOLD, color=ink_on(color)),
        width=BADGE_SIZE,
        height=BADGE_SIZE,
        border_radius=5,
        bgcolor=color,
        alignment=ft.Alignment.CENTER,
    )


def short(name: str, limit: int = CHIP_NAME_MAX) -> str:
    return name if len(name) <= limit else name[: limit - 1].rstrip(" ,") + "…"


def quantity_label(grams: float, portion: dict | None, per_portion: bool) -> str:
    """« 100 g », ou « 1 fruit · 150 g » quand on compare par portion."""
    if per_portion and portion:
        return f"1 {portion['label']} · {fmt(grams)} g"
    if per_portion:
        return f"{fmt(grams)} g (pas de portion connue)"
    return f"{fmt(grams)} g"


def bar(ratio: float, scale: float, color: str) -> ft.Control:
    """La barre seule : sa longueur est `ratio` rapporté au bout de l'axe `scale`. Au-delà de
    l'axe, elle est pleine et suivie d'un chevron « dépasse »."""
    overflow = ratio > scale
    units = 0 if ratio <= 0 else max(BAR_MIN_UNITS, min(BAR_UNITS, round(ratio / scale * BAR_UNITS)))
    parts: list[ft.Control] = []
    if units:
        parts.append(
            ft.Container(
                expand=units,
                height=BAR_HEIGHT,
                bgcolor=color,
                border_radius=ft.BorderRadius.only(top_right=BAR_RADIUS, bottom_right=BAR_RADIUS),
            )
        )
    if units < BAR_UNITS:
        parts.append(ft.Container(expand=BAR_UNITS - units, height=BAR_HEIGHT))
    track = ft.Row(parts, spacing=0, expand=True)
    if not overflow:
        return track
    return ft.Row(
        [track, ft.Icon(ft.Icons.KEYBOARD_DOUBLE_ARROW_RIGHT, size=14, color=color, tooltip="Dépasse l'échelle")],
        spacing=0,
        expand=True,
    )


def value_text(share: dict, unit: str, best: bool) -> ft.Control:
    """« 3.3 mg · 22 % » ; en gras pour l'aliment qui en apporte le plus."""
    if share["amount"] <= 0:
        return ft.Text("–", size=12, color=ft.Colors.GREY_500, width=VALUE_WIDTH, text_align=ft.TextAlign.RIGHT)
    return ft.Text(
        f"{fmt(share['amount'])} {unit} · {share['ratio'] * 100:.0f} %",
        size=12,
        weight=ft.FontWeight.BOLD if best else None,
        color=None if best else MUTED,
        width=VALUE_WIDTH,
        text_align=ft.TextAlign.RIGHT,
        no_wrap=True,
    )


def reference_line(scale: float) -> ft.Control:
    """Trait vertical à 100 % de l'apport recommandé, superposé aux barres d'une carte."""
    units = round(BAR_UNITS / scale)
    return ft.Row(
        [
            ft.Container(width=BADGE_SIZE),
            ft.Row(
                [
                    ft.Container(expand=units),
                    ft.Container(width=1, bgcolor=REFERENCE_LINE_COLOR),
                    ft.Container(expand=BAR_UNITS - units),
                ],
                spacing=0,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            ft.Container(width=VALUE_WIDTH),
        ],
        spacing=ROW_SPACING,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        left=0,
        right=0,
        top=0,
        bottom=0,
    )


def card(content: ft.Control) -> ft.Control:
    return ft.Container(content, padding=14, border_radius=14, bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST)


def nutrient_card(
    nutrient: dict, recommended: float, selection: list[dict], shares: dict[int, dict[str, dict]], scale: float
) -> ft.Control:
    """La carte d'un nutriment : son nom, l'apport recommandé, et une barre par aliment."""
    key = nutrient["key"]
    best = best_slots(shares, key)
    header = ft.Row(
        [
            ft.Text(nutrient["label"], size=15, weight=ft.FontWeight.W_600, expand=True),
            ft.Text(f"recommandé : {fmt(recommended)} {nutrient['unit']}", size=12, color=MUTED),
        ],
        vertical_alignment=ft.CrossAxisAlignment.END,
    )
    if all(shares[s["slot"]][key]["amount"] <= 0 for s in selection):
        # Rien à comparer : une ligne suffit, plutôt qu'une pile de barres vides.
        none = "Cet aliment n'en apporte pas." if len(selection) == 1 else "Aucun de ces aliments n'en apporte."
        return card(ft.Column([header, ft.Text(none, size=12, color=ft.Colors.GREY_500)], spacing=6))
    rows = ft.Column(
        [
            ft.Row(
                [
                    badge(s["slot"]),
                    bar(shares[s["slot"]][key]["ratio"], scale, CHART_COLORS[s["slot"]]),
                    value_text(shares[s["slot"]][key], nutrient["unit"], s["slot"] in best),
                ],
                spacing=ROW_SPACING,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            for s in selection
        ],
        spacing=6,
    )
    bars: ft.Control = ft.Stack([rows, reference_line(scale)]) if scale > 1 else rows
    return card(ft.Column([header, bars], spacing=10))


def show_compare(ctx: AppContext) -> None:
    page = ctx.page
    profile = ctx.get_profile()
    recommended = recommended_intakes(profile)
    shown = selected_nutrients(profile)
    keys = [n["key"] for n in shown]
    # Un aliment perso supprimé ou renommé depuis la dernière visite sort de la comparaison.
    ctx.compare_selection[:] = valid_selection(ctx.compare_selection, ctx.foods)
    selection = ctx.compare_selection

    shortcuts_holder = ft.Column(spacing=6)
    legend_holder = ft.Column(spacing=6)
    chart_holder = ft.Column(spacing=10)

    def pick(name: str) -> None:
        """Un aliment est choisi (suggestion, Entrée ou raccourci) : il rejoint la comparaison."""
        add_food(selection, name, COMPARE_MAX_FOODS)
        food_field.value = ""
        food_field.error = None
        suggestions_col.controls = []
        refresh()

    def on_submit(e=None) -> None:
        """Entrée : prend l'aliment tapé, sinon la première suggestion."""
        text = food_field.value or ""
        food = find_food(text, ctx.foods)
        matches = [food["name"]] if food else search_foods(text, ctx.foods)
        if matches:
            pick(matches[0])
        elif text.strip():
            food_field.error = "Aucun aliment ne correspond"
            page.update()

    def unpick(name: str) -> None:
        remove_food(selection, name)
        refresh()

    def on_quantity_change(e) -> None:
        ctx.compare_per_portion = "portion" in e.control.selected
        refresh()

    food_field, suggestions_col = make_food_input(ctx, on_submit, on_pick=pick, expand=True)
    food_field.label = "Ajouter un aliment à comparer"
    food_field.prefix_icon = ft.Icons.SEARCH
    quantity_switch = ft.SegmentedButton(
        segments=[
            ft.Segment(value="100g", label=ft.Text("Pour 100 g")),
            ft.Segment(value="portion", label=ft.Text("Par portion")),
        ],
        selected=["portion" if ctx.compare_per_portion else "100g"],
        show_selected_icon=False,
        on_change=on_quantity_change,
    )

    def legend_row(item: dict, grams: float) -> ft.Control:
        portion = portion_for(item["name"], ctx.foods, ctx.state["food_units"])
        return ft.Container(
            ft.Row(
                [
                    badge(item["slot"]),
                    ft.Column(
                        [
                            ft.Text(item["name"], size=14, weight=ft.FontWeight.W_600),
                            ft.Text(quantity_label(grams, portion, ctx.compare_per_portion), size=12, color=MUTED),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        icon_size=18,
                        tooltip="Retirer de la comparaison",
                        on_click=lambda e: unpick(item["name"]),
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(left=12, right=2, top=4, bottom=4),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
        )

    def shortcuts() -> list[ft.Control]:
        """Raccourcis : les aliments les plus souvent notés qui ne sont pas déjà comparés."""
        if len(selection) >= COMPARE_MAX_FOODS:
            return []
        frequent = frequent_foods(ctx.state["journal"], ctx.foods, COMPARE_SUGGESTIONS + len(selection))
        names = [n for n in frequent if not is_selected(selection, n)][:COMPARE_SUGGESTIONS]
        if not names:
            return []
        chips = [ft.Chip(label=ft.Text(short(n), size=12), on_click=lambda e, n=n: pick(n), tooltip=n) for n in names]
        return [ft.Text("Souvent notés", size=12, color=MUTED), ft.Row(chips, scroll=ft.ScrollMode.HIDDEN, spacing=6)]

    def empty_state() -> list[ft.Control]:
        return [
            ft.Container(
                ft.Column(
                    [
                        ft.Icon(ft.Icons.BAR_CHART, size=48, color=ft.Colors.GREY_500),
                        ft.Text("Cherche un aliment pour voir ce qu'il apporte.", size=16, weight=ft.FontWeight.W_600),
                        ft.Text(
                            f"Ajoutes-en jusqu'à {COMPARE_MAX_FOODS} pour les comparer, nutriment par nutriment.",
                            color=MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                padding=ft.Padding.symmetric(vertical=32),
                alignment=ft.Alignment.CENTER,
            )
        ]

    def chart(grams: dict[int, float]) -> list[ft.Control]:
        if not shown:
            return [ft.Text("Aucun nutriment suivi : choisis-en dans ton profil.", color=MUTED)]
        shares = {
            s["slot"]: nutrient_shares(s["name"], grams[s["slot"]], ctx.foods, recommended, keys) for s in selection
        }
        scale = axis_max([share["ratio"] for by_key in shares.values() for share in by_key.values()], COMPARE_SCALE_MAX)
        caption = f"Longueur des barres : part de ton apport journalier recommandé. Barre pleine = {scale * 100:.0f} %"
        caption += ", trait vertical = 100 %." if scale > 1 else "."
        if any(share["ratio"] > scale for by_key in shares.values() for share in by_key.values()):
            caption += " Un chevron » signale un apport qui dépasse l'échelle."
        controls: list[ft.Control] = [ft.Text(caption, size=12, color=MUTED)]
        for group in dict.fromkeys(n["group"] for n in shown):
            controls.append(ft.Text(group, size=18, weight=ft.FontWeight.W_600))
            controls += [
                nutrient_card(n, recommended[n["key"]], selection, shares, scale) for n in shown if n["group"] == group
            ]
        return controls

    def refresh() -> None:
        full = len(selection) >= COMPARE_MAX_FOODS
        food_field.disabled = full
        food_field.hint_text = (
            f"{COMPARE_MAX_FOODS} aliments au maximum : retires-en un" if full else "ex : lentilles cuites"
        )
        grams = {
            s["slot"]: compared_grams(s["name"], ctx.foods, ctx.state["food_units"], ctx.compare_per_portion)
            for s in selection
        }
        shortcuts_holder.controls = shortcuts()
        legend_holder.controls = [legend_row(s, grams[s["slot"]]) for s in selection]
        quantity_switch.visible = bool(selection)
        chart_holder.controls = chart(grams) if selection else empty_state()
        page.update()

    show_screen(
        ctx,
        ft.Column(
            [
                screen_title("Comparer", "Ce que chaque aliment apporte, nutriment par nutriment"),
                ft.Container(height=4),
                ft.Row([food_field]),
                suggestions_col,
                shortcuts_holder,
                legend_holder,
                ft.Row([quantity_switch], alignment=ft.MainAxisAlignment.CENTER),
                chart_holder,
            ],
            spacing=10,
        ),
        tab="comparer",
    )
    refresh()
