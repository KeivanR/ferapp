"""Page principale : saisie du jour, cercles de complétion par nutriment, journal des repas."""

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
from .layout import screen_title, show_screen
from .nutrient_detail import show_nutrient_detail
from .rings import rings_grid
from .widgets import QuantityInput, fmt, make_food_input, make_grams_input, validate, validate_with_quantity


def show_main(ctx: AppContext) -> None:
    page = ctx.page
    profile = ctx.get_profile()
    recommended = recommended_intakes(profile)
    shown = selected_nutrients(profile)

    rings_holder = ft.Container()  # grille des cercles (ui/rings.py), reconstruite à chaque refresh()
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
    quantity = QuantityInput(ctx, on_submit=on_quantity_submit, hint_text="Tape la quantité puis Entrée", expand=True)
    quantity_row = ft.Row([quantity.control], visible=False)

    def open_nutrient_detail(nutrient: dict) -> None:
        """Toucher un cercle : il s'ouvre en grand, avec la part de chaque aliment du jour."""
        show_nutrient_detail(ctx, nutrient, ctx.entries_today(), recommended[nutrient["key"]])

    def refresh():
        entries = ctx.entries_today()
        totals = daily_totals(entries, ctx.foods)
        ratios = completion(totals, recommended)
        rings_holder.content = rings_grid(shown, ratios, totals, recommended, on_click=open_nutrient_detail)
        entries_col.controls = [build_entry_tile(i, e) for i, e in enumerate(entries)] or [
            ft.Text("Rien d'ajouté pour l'instant.", color=ft.Colors.GREY_600)
        ]
        page.update()

    def build_entry_tile(i: int, e: dict) -> ft.Control:
        """Une ligne du journal : aliment, grammage et nutriment le plus apporté."""
        top = top_nutrient(e, ctx.foods, recommended, shown)
        if top:
            detail = (
                f"{top['label']} : {fmt(top['amount'])} {top['unit']} ({top['share'] * 100:.0f} % de l'apport du jour)"
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

    show_screen(
        ctx,
        ft.Column(
            [
                screen_title(
                    "Aujourd'hui",
                    datetime.date.today().strftime("%d/%m/%Y"),
                    trailing=ft.IconButton(
                        ft.Icons.PERSON_OUTLINE, tooltip="Mon profil", on_click=lambda e: ctx.router.show_profile()
                    ),
                ),
                ft.Container(height=8),
                rings_holder,
                ft.Container(height=8),
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
        tab="accueil",
    )
    refresh()
