"""Page principale : saisie du jour, cercles de complétion par nutriment, journal des repas.
"""

from __future__ import annotations

import datetime

import flet as ft

from nutrition import completion, daily_totals, recommended_intakes, selected_nutrients, top_nutrient

from .context import AppContext
from .style import COLOR_DONE, COLOR_TODO, RING_SIZE, RING_STROKE
from .widgets import fmt, make_food_input, make_grams_input, validate


def show_main(ctx: AppContext) -> None:
    page = ctx.page
    profile = ctx.get_profile()
    recommended = recommended_intakes(profile)
    shown = selected_nutrients(profile)

    rings_row = ft.Row(wrap=True, alignment=ft.MainAxisAlignment.CENTER, spacing=6, run_spacing=16)
    entries_col = ft.Column(spacing=0)

    food_field, suggestions_col = make_food_input(ctx, lambda e: add_entry(), expand=True)
    grams_field = make_grams_input(ctx, lambda e: add_entry(), width=110)

    def build_ring(n: dict, ratio: float, total: float, rec: float) -> ft.Control:
        done = ratio >= 1
        color = COLOR_DONE if done else COLOR_TODO
        size = RING_SIZE
        return ft.Column(
            [
                ft.Stack(
                    [
                        ft.ProgressRing(
                            value=min(ratio, 1.0),
                            stroke_width=RING_STROKE,
                            width=size,
                            height=size,
                            color=color,
                            bgcolor=ft.Colors.GREY_200,
                        ),
                        ft.Container(
                            width=size,
                            height=size,
                            alignment=ft.Alignment.CENTER,
                            content=(
                                ft.Icon(ft.Icons.CHECK, color=color, size=30)
                                if done
                                else ft.Text(f"{ratio * 100:.0f}%", weight=ft.FontWeight.BOLD, size=16)
                            ),
                        ),
                    ],
                    width=size,
                    height=size,
                ),
                ft.Text(n["label"], weight=ft.FontWeight.W_600, size=14),
                ft.Text(f"{fmt(total)} / {fmt(rec)} {n['unit']}", size=11, color=ft.Colors.GREY_700),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=3,
            width=112,
        )

    def refresh():
        entries = ctx.entries_today()
        totals = daily_totals(entries, ctx.foods)
        ratios = completion(totals, recommended)
        rings_row.controls = [
            build_ring(n, ratios[n["key"]], totals[n["key"]], recommended[n["key"]]) for n in shown
        ]
        entries_col.controls = [build_entry_tile(i, e) for i, e in enumerate(entries)] or [
            ft.Text("Rien d'ajouté pour l'instant.", color=ft.Colors.GREY_600)
        ]
        page.update()

    def build_entry_tile(i: int, e: dict) -> ft.Control:
        """Une ligne du journal : aliment, grammage et nutriment le plus apporté."""
        top = top_nutrient(e, ctx.foods, recommended, shown)
        if top:
            detail = (
                f"{top['label']} : {fmt(top['amount'])} {top['unit']} "
                f"({top['share'] * 100:.0f} % de l'apport du jour)"
            )
        else:
            detail = "Aucune donnée pour les nutriments choisis"
        return ft.ListTile(
            title=ft.Text(f"{e['food']} — {fmt(e['grams'])} g"),
            subtitle=ft.Text(detail, size=12, color=ft.Colors.GREEN_800 if top else ft.Colors.GREY_600),
            trailing=ft.Row(
                [
                    ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="Modifier", on_click=lambda ev, i=i: open_edit(i)),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE, tooltip="Supprimer", on_click=lambda ev, i=i: delete_entry(i)
                    ),
                ],
                tight=True,
                spacing=0,
            ),
            on_click=lambda ev, i=i: open_edit(i),
        )

    def add_entry(e=None):
        checked = validate(ctx, food_field, grams_field)
        if checked is None:
            return
        food, grams = checked
        ctx.entries_today().append({"food": food["name"], "grams": grams})
        ctx.save()
        food_field.value = ""
        grams_field.value = ""
        suggestions_col.controls = []
        refresh()

    def delete_entry(index: int):
        entries = ctx.entries_today()
        if 0 <= index < len(entries):
            entries.pop(index)
            ctx.save()
            refresh()

    def open_edit(index: int):
        """Fenêtre pour corriger l'aliment et/ou le grammage d'une entrée du jour."""
        entries = ctx.entries_today()
        if not 0 <= index < len(entries):
            return
        entry = entries[index]

        edit_food, edit_suggestions = make_food_input(ctx, lambda e: save_edit(), width=300)
        edit_food.value = entry["food"]
        edit_grams = make_grams_input(ctx, lambda e: save_edit(), width=300)
        edit_grams.value = f"{entry['grams']:g}"

        def save_edit(e=None):
            checked = validate(ctx, edit_food, edit_grams)
            if checked is None:
                return
            food, grams = checked
            entries[index] = {"food": food["name"], "grams": grams}
            ctx.save()
            page.pop_dialog()
            refresh()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Modifier l'entrée"),
                content=ft.Column([edit_food, edit_suggestions, edit_grams], tight=True, width=300),
                scrollable=True,
                actions=[
                    ft.TextButton("Annuler", on_click=lambda e: page.pop_dialog()),
                    ft.FilledButton("Enregistrer", on_click=save_edit),
                ],
            )
        )

    page.appbar = None
    page.clean()
    page.add(
        ft.SafeArea(
            ft.Container(
                padding=ft.Padding.only(left=16, right=16, top=8, bottom=24),
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text("Aujourd'hui", size=26, weight=ft.FontWeight.BOLD),
                                        ft.Text(datetime.date.today().strftime("%d/%m/%Y"), color=ft.Colors.GREY_700),
                                    ],
                                    spacing=0,
                                ),
                                ft.IconButton(
                                    ft.Icons.PERSON_OUTLINE,
                                    tooltip="Mon profil",
                                    on_click=lambda e: ctx.router.show_profile(),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Row([food_field, grams_field], vertical_alignment=ft.CrossAxisAlignment.START),
                        suggestions_col,
                        ft.Row(
                            [
                                ft.FilledButton("Ajouter", icon=ft.Icons.ADD, on_click=add_entry),
                                ft.TextButton(
                                    "Nouvel aliment",
                                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                    on_click=lambda e: ctx.router.show_custom_food(),
                                ),
                            ],
                            wrap=True,
                        ),
                        ft.Divider(height=24),
                        rings_row,
                        ft.Divider(height=24),
                        ft.Text("Repas du jour", size=18, weight=ft.FontWeight.W_600),
                        entries_col,
                    ],
                    spacing=8,
                ),
            )
        )
    )
    refresh()
