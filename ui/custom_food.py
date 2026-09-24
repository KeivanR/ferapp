"""Écran « Nouvel aliment » : ajoute un aliment personnalisé, saisi à la main (teneurs pour
100 g) ou en recette (liste d'aliments existants avec leur grammage).
"""

from __future__ import annotations

import flet as ft

from nutrition import NUTRIENTS, normalize, parse_grams, parse_nutrient_value, recipe_per100

from .context import AppContext
from .style import COLOR_CUSTOM
from .widgets import fmt, make_food_input, make_grams_input, validate


def show_custom_food(ctx: AppContext) -> None:
    page = ctx.page

    def clear_error(field: ft.TextField):
        if field.error:
            field.error = None
            page.update()

    name_field = ft.TextField(
        label="Nom de l'aliment",
        hint_text="ex : soupe de lentilles maison",
        on_change=lambda e: clear_error(name_field),
    )

    # --- Unité familière optionnelle (ex. « 1 part » = 250 g) — voir ui/widgets.QuantityInput.
    # Les deux champs vont ensemble : soit aucun des deux, soit les deux. D'autres unités pourront
    # être ajoutées plus tard pour ce même aliment depuis l'écran principal.
    unit_label_field = ft.TextField(
        label="Nom d'une unité (facultatif)",
        hint_text="ex : fruit, verre, part",
        width=220,
        on_change=lambda e: clear_error(unit_label_field),
    )
    unit_grams_field = ft.TextField(
        label="= combien de grammes ?",
        width=220,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: clear_error(unit_grams_field),
    )

    # --- Mode 1 : teneurs saisies à la main (pour 100 g) ---
    value_fields = {
        n["key"]: ft.TextField(label=f"{n['label']} ({n['unit']})", width=170, keyboard_type=ft.KeyboardType.NUMBER)
        for n in NUTRIENTS
    }
    for f in value_fields.values():
        f.on_change = lambda e, f=f: clear_error(f)
    manual_children: list[ft.Control] = [
        ft.Text("Teneur pour 100 g d'aliment (case vide = 0)", color=ft.Colors.GREY_700)
    ]
    for group in dict.fromkeys(n["group"] for n in NUTRIENTS):
        manual_children.append(ft.Text(group, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700))
        manual_children.append(
            ft.Row(
                [value_fields[n["key"]] for n in NUTRIENTS if n["group"] == group],
                wrap=True,
                spacing=10,
                run_spacing=10,
            )
        )
    manual_col = ft.Column(manual_children, spacing=8)

    # --- Mode 2 : recette = liste d'aliments avec leur grammage ---
    ingredients: list[dict] = []
    ing_food, ing_suggestions = make_food_input(ctx, lambda e: add_ingredient(), expand=True)
    ing_food.label = "Ingrédient"
    ing_grams = make_grams_input(ctx, lambda e: add_ingredient(), width=110)
    ingredients_col = ft.Column(spacing=0)
    total_text = ft.Text("Aucun ingrédient pour l'instant.", color=ft.Colors.GREY_700)
    recipe_error = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)
    final_weight = ft.TextField(label="Poids final du plat (g), facultatif", keyboard_type=ft.KeyboardType.NUMBER)
    final_weight.on_change = lambda e: clear_error(final_weight)

    def refresh_ingredients():
        ingredients_col.controls = [
            ft.ListTile(
                title=ft.Text(f"{ing['food']} — {fmt(ing['grams'])} g"),
                trailing=ft.IconButton(
                    ft.Icons.DELETE_OUTLINE, tooltip="Retirer", on_click=lambda ev, idx=idx: remove_ingredient(idx)
                ),
                dense=True,
            )
            for idx, ing in enumerate(ingredients)
        ]
        total = sum(i["grams"] for i in ingredients)
        total_text.value = (
            f"Poids total des ingrédients : {fmt(total)} g" if ingredients else "Aucun ingrédient pour l'instant."
        )
        page.update()

    def add_ingredient(e=None):
        checked = validate(ctx, ing_food, ing_grams)
        if checked is None:
            return
        food, grams = checked
        ingredients.append({"food": food["name"], "grams": grams})
        ing_food.value = ""
        ing_grams.value = ""
        ing_suggestions.controls = []
        recipe_error.visible = False
        refresh_ingredients()

    def remove_ingredient(idx: int):
        if 0 <= idx < len(ingredients):
            ingredients.pop(idx)
            refresh_ingredients()

    recipe_col = ft.Column(
        [
            ft.Text("Ajoute les aliments qui composent la recette", color=ft.Colors.GREY_700),
            ft.Row([ing_food, ing_grams], vertical_alignment=ft.CrossAxisAlignment.START),
            ing_suggestions,
            ft.OutlinedButton("Ajouter l'ingrédient", icon=ft.Icons.ADD, on_click=add_ingredient),
            ingredients_col,
            total_text,
            recipe_error,
            final_weight,
            ft.Text(
                "Vide = somme des ingrédients. À remplir si le plat perd ou gagne de l'eau à la cuisson.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
        ],
        spacing=8,
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    def on_mode_change(e):
        manual_col.visible = mode.value == "manual"
        recipe_col.visible = mode.value == "recipe"
        page.update()

    mode = ft.RadioGroup(
        value="manual",
        on_change=on_mode_change,
        content=ft.Column(
            [
                ft.Radio(value="manual", label="Saisir les nutriments"),
                ft.Radio(value="recipe", label="Recette (à partir d'autres aliments)"),
            ],
            spacing=0,
        ),
    )

    def save_custom(e=None):
        name = " ".join((name_field.value or "").split())
        ok = True
        if not name:
            name_field.error = "Donne un nom à l'aliment"
            ok = False
        elif normalize(name) in ctx.foods:
            name_field.error = "Un aliment porte déjà ce nom"
            ok = False

        # Unité familière : les deux champs ensemble, ou aucun des deux.
        unit_label = " ".join((unit_label_field.value or "").split())
        unit_grams_text = (unit_grams_field.value or "").strip()
        unit_grams = None
        if unit_label or unit_grams_text:
            if not unit_label:
                unit_label_field.error = "Donne un nom à l'unité"
                ok = False
            elif normalize(unit_label) == "grammes":
                unit_label_field.error = "« grammes » est réservé, choisis un autre nom"
                ok = False
            if not unit_grams_text:
                unit_grams_field.error = "Indique le nombre de grammes"
                ok = False
            else:
                unit_grams = parse_grams(unit_grams_text)
                if unit_grams is None:
                    unit_grams_field.error = "Invalide"
                    ok = False

        food: dict = {"name": name}
        if mode.value == "manual":
            per100 = {}
            for n in NUTRIENTS:
                value = parse_nutrient_value(value_fields[n["key"]].value or "")
                if value is None:
                    value_fields[n["key"]].error = "Invalide"
                    ok = False
                else:
                    per100[n["key"]] = value
            food.update(kind="manual", per100=per100)
        else:
            weight = None
            if (final_weight.value or "").strip():
                weight = parse_grams(final_weight.value)
                if weight is None:
                    final_weight.error = "Invalide"
                    ok = False
            if not ingredients:
                recipe_error.value = "Ajoute au moins un ingrédient"
                recipe_error.visible = True
                ok = False
            if ok:
                food.update(
                    kind="recipe",
                    ingredients=[dict(i) for i in ingredients],
                    final_weight=weight,
                    per100=recipe_per100(ingredients, ctx.foods, weight),
                )
        if not ok:
            page.update()
            return

        ctx.add_custom_food(food)
        if unit_label and unit_grams is not None:
            try:
                ctx.add_food_unit(name, unit_label, unit_grams)
            except ValueError:
                # Garde-fou seulement : l'aliment est créé quoi qu'il arrive, l'unité pourra être
                # ajoutée depuis l'écran principal (bouton « Nouvelle unité »).
                pass
        ctx.router.show_main()

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
                                ft.IconButton(
                                    ft.Icons.ARROW_BACK, tooltip="Retour", on_click=lambda e: ctx.router.show_main()
                                ),
                                ft.Text("Nouvel aliment", size=24, weight=ft.FontWeight.BOLD),
                            ]
                        ),
                        ft.Text(
                            "Il apparaîtra en orange dans les suggestions : il ne vient pas de la base officielle.",
                            color=COLOR_CUSTOM,
                            size=13,
                        ),
                        name_field,
                        ft.Row([unit_label_field, unit_grams_field], wrap=True, spacing=10, run_spacing=10),
                        ft.Text(
                            "Facultatif : une unité pratique pour la saisie ensuite (ex. « 1 fruit » plutôt "
                            "qu'en grammes). D'autres unités pourront être ajoutées plus tard, pour ce ou "
                            "d'autres aliments, depuis l'écran principal.",
                            size=12,
                            color=ft.Colors.GREY_700,
                        ),
                        mode,
                        manual_col,
                        recipe_col,
                        ft.Row(
                            [
                                ft.TextButton("Annuler", on_click=lambda e: ctx.router.show_main()),
                                ft.FilledButton("Enregistrer l'aliment", on_click=save_custom),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                        ),
                    ],
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
            )
        )
    )
