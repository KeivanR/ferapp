"""Page principale : saisie du jour, cercles de complétion par nutriment, journal des repas.
"""

from __future__ import annotations

import datetime

import flet as ft

from nutrition import (
    completion,
    daily_totals,
    find_food,
    recommended_intakes,
    search_foods,
    selected_nutrients,
    top_nutrient,
)

from .context import AppContext
from .style import COLOR_DONE, COLOR_TODO, RING_SIZE, RING_SIZE_MAX, RING_STROKE
from .widgets import QuantityInput, fmt, make_food_input, make_grams_input, validate, validate_with_quantity


def ring_size_for(count: int) -> int:
    """Diamètre des cercles selon le nombre de nutriments suivis : très grand (jusqu'à
    RING_SIZE_MAX) s'il y en a peu, jusqu'au minimum RING_SIZE s'il y en a beaucoup — pour
    qu'un profil avec un seul nutriment lui laisse toute la place."""
    if count <= 1:
        return RING_SIZE_MAX
    size = round(RING_SIZE_MAX / count**0.5)
    return max(RING_SIZE, min(size, RING_SIZE_MAX))


def show_main(ctx: AppContext) -> None:
    page = ctx.page
    profile = ctx.get_profile()
    recommended = recommended_intakes(profile)
    shown = selected_nutrients(profile)

    # Centrés par rapport à la page : ft.Row(wrap=True) (un « Wrap » Flutter) ne prend que la
    # largeur de son contenu, donc son alignement centré n'a d'effet qu'une fois placé dans un
    # Row englobant qui, lui, occupe toute la largeur disponible.
    rings_wrap = ft.Row(wrap=True, alignment=ft.MainAxisAlignment.CENTER, spacing=16, run_spacing=16)
    rings_row = ft.Row([rings_wrap], alignment=ft.MainAxisAlignment.CENTER)
    entries_col = ft.Column(spacing=0)

    # La quantité se saisit en grammes ou dans une unité familière propre à l'aliment (ex. « 2
    # fruits ») — voir ui/widgets.QuantityInput. `on_food_changed` la relie au champ aliment pour
    # recharger ses unités à chaque fois qu'il change. La barre « Quantité » n'est affichée qu'une
    # fois un aliment reconnu (choisi dans les suggestions ou tapé exactement) ; elle disparaît
    # après l'ajout. Pas de bouton pour valider : Entrée dans le champ quantité ajoute l'aliment ;
    # Entrée dans le champ aliment choisit la 1re suggestion si besoin puis passe à la quantité
    # (ou ajoute directement si elle est déjà remplie).
    def on_food_changed(name: str) -> None:
        quantity_row.visible = find_food(name, ctx.foods) is not None
        quantity.set_food(name)  # rafraîchit aussi la page

    async def on_quantity_submit(e=None):
        await add_entry()

    async def on_food_submit(e=None):
        if find_food(food_field.value or "", ctx.foods) is None:
            matches = search_foods(food_field.value or "", ctx.foods)
            if not matches:
                food_field.error = "Choisis un aliment dans la liste"
                page.update()
                return
            food_field.value = matches[0]  # ex. « Pain (aliment moyen) » en tapant « pain »
            food_field.error = None
            suggestions_col.controls = []
            on_food_changed(matches[0])
        if quantity.is_empty():
            await quantity.focus()
        else:
            await add_entry()

    food_field, suggestions_col = make_food_input(ctx, on_food_submit, on_food_changed=on_food_changed, expand=True)
    quantity = QuantityInput(
        ctx, on_submit=on_quantity_submit, hint_text="Tape la quantité puis Entrée", expand=True
    )
    quantity_row = ft.Row([quantity.control], visible=False)

    def build_ring(n: dict, ratio: float, total: float, rec: float, size: int) -> ft.Control:
        done = ratio >= 1
        color = COLOR_DONE if done else COLOR_TODO
        # Un plus gros cercle mérite un trait, un texte et une coche proportionnellement plus gros.
        stroke = max(RING_STROKE, round(RING_STROKE * size / RING_SIZE))
        pct_size = max(16, size // 6)
        icon_size = max(28, size // 4)
        return ft.Column(
            [
                ft.Stack(
                    [
                        ft.ProgressRing(
                            value=min(ratio, 1.0),
                            stroke_width=stroke,
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
                                ft.Icon(ft.Icons.CHECK, color=color, size=icon_size)
                                if done
                                else ft.Text(f"{ratio * 100:.0f}%", weight=ft.FontWeight.BOLD, size=pct_size)
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
            width=max(112, size + 24),
        )

    def refresh():
        entries = ctx.entries_today()
        totals = daily_totals(entries, ctx.foods)
        ratios = completion(totals, recommended)
        size = ring_size_for(len(shown))
        rings_wrap.controls = [
            build_ring(n, ratios[n["key"]], totals[n["key"]], recommended[n["key"]], size) for n in shown
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

    async def add_entry(e=None):
        """Ajoute l'aliment saisi au journal du jour (déclenché par Entrée, pas de bouton)."""
        if not (food_field.value or "").strip() and quantity.is_empty():
            return  # Entrée sur des champs vides : rien à faire, pas de message d'erreur
        checked = validate_with_quantity(ctx, food_field, quantity)
        if checked is None:
            return
        food, grams = checked
        ctx.entries_today().append({"food": food["name"], "grams": grams})
        ctx.remember_unit(food["name"], quantity.unit_label)  # présélectionnée la prochaine fois
        ctx.save()
        food_field.value = ""
        suggestions_col.controls = []
        quantity.reset()
        on_food_changed("")  # aliment vidé : barre « Quantité » masquée jusqu'au prochain aliment
        refresh()
        await food_field.focus()  # prêt pour l'aliment suivant

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
                        ft.Container(height=16),
                        rings_row,
                        ft.Container(height=16),
                        ft.Row([food_field]),
                        suggestions_col,
                        quantity_row,
                        ft.Row(
                            [
                                # Ouvre l'écran de création d'un aliment personnalisé (ui/custom_food.py).
                                ft.TextButton(
                                    "Ajouter",
                                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                    tooltip="Ajouter un aliment qui n'est pas dans la liste",
                                    on_click=lambda e: ctx.router.show_custom_food(),
                                ),
                            ],
                        ),
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
