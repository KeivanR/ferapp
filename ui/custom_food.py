"""Écran de création OU de modification d'un aliment personnalisé, saisi à la main (teneurs pour
100 g) ou en recette (liste d'aliments existants avec leur grammage).

  - création : `show_custom_food(ctx)` — bouton « Ajouter » de l'accueil, ou « Nouvel aliment »
    de l'onglet Mes aliments ;
  - modification : `show_custom_food(ctx, name="Soupe maison")` — bouton « Modifier » de la fiche
    de l'aliment (ui/food_detail.py).
    Le formulaire est prérempli ; un renommage ou de nouvelles teneurs s'appliquent aussi aux
    repas déjà notés et aux recettes qui l'utilisent (voir custom_foods.py).

`back()` ramène à l'écran d'où l'on vient (après Enregistrer, Annuler ou ←).
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from custom_foods import depends_on
from nutrition import GRAMS_UNIT, NUTRIENTS, normalize, parse_grams, parse_nutrient_value, recipe_per100

from .context import AppContext
from .layout import show_screen
from .style import COLOR_CUSTOM
from .widgets import fmt, make_food_input, make_grams_input, validate


def field_value(value: float | None) -> str:
    """Valeur préremplie dans un champ : vide pour 0 (« case vide = 0 »), virgule française."""
    if not value:
        return ""
    return f"{round(value, 4):g}".replace(".", ",")


def intro_text(existing: dict | None, usage: dict) -> ft.Control:
    """Phrase d'explication en haut de l'écran."""
    if existing is None:
        return ft.Text(
            spans=[
                ft.TextSpan(
                    "Tu ne trouves pas un aliment dans la liste ? Ajoute-le ici, en saisissant ses nutriments "
                    "ou comme une recette faite d'autres aliments. Il apparaîtra ensuite "
                ),
                ft.TextSpan(
                    "en orange, avec la mention « perso »",
                    style=ft.TextStyle(color=COLOR_CUSTOM, weight=ft.FontWeight.W_600),
                ),
                ft.TextSpan(
                    ", en tête des suggestions quand tu le tapes, pour le distinguer des aliments de la base "
                    "officielle. Tu retrouves tous tes aliments dans l'onglet «\u00a0Mes aliments\u00a0»."
                ),
            ],
            size=14,
        )
    used = []
    meals = usage["meals"]
    if meals:
        used.append(
            f"aux {meals} repas déjà notés avec cet aliment" if meals > 1 else "au repas déjà noté avec cet aliment"
        )
    if usage["recipes"]:
        used.append("aux recettes qui l'utilisent (" + ", ".join(usage["recipes"]) + ")")
    applies = " Les modifications s'appliqueront aussi " + " et ".join(used) + "." if used else ""
    return ft.Text("Corrige le nom, les nutriments ou la recette, puis enregistre." + applies, size=14)


def show_custom_food(
    ctx: AppContext,
    name: str | None = None,
    back: Callable[[], None] | None = None,
    on_saved: Callable[[str], None] | None = None,
) -> None:
    """`name` : aliment perso à modifier (None = en créer un) ; `back` : retour (défaut : l'accueil) ;
    `on_saved(nom)` : appelé à la place de `back` après Enregistrer, avec le nom enregistré (qui a
    pu changer) — sert à la fiche de l'aliment pour se rouvrir sous le bon nom."""
    page = ctx.page
    existing = ctx.custom_food(name) if name else None
    editing = existing is not None
    back = back or (lambda: ctx.router.show_main(ctx.home_day))

    def clear_error(field: ft.TextField):
        if field.error:
            field.error = None
            page.update()

    name_field = ft.TextField(
        label="Nom de l'aliment",
        hint_text="ex : soupe de lentilles maison",
        value=existing["name"] if editing else None,
        on_change=lambda e: clear_error(name_field),
    )

    # --- Unités familières (ex. « 1 part » = 250 g) — voir ui/widgets.QuantityInput.
    # En modification, celles déjà définies sont listées (et peuvent être retirées) ; les deux
    # champs permettent d'en ajouter une : soit aucun des deux, soit les deux.
    units = ctx.user_units(existing["name"]) if editing else []
    removed_units: list[str] = []  # retirées à l'enregistrement seulement (Annuler les garde)
    units_col = ft.Column(spacing=0)

    def refresh_units():
        kept = [u for u in units if u["label"] not in removed_units]
        units_col.controls = [
            ft.ListTile(
                title=ft.Text(f"1 {u['label']} = {fmt(u['grams'])} g"),
                trailing=ft.IconButton(
                    ft.Icons.DELETE_OUTLINE, tooltip="Retirer cette unité", on_click=lambda e, u=u: remove_unit(u)
                ),
                dense=True,
            )
            for u in kept
        ]
        page.update()

    def remove_unit(unit: dict):
        removed_units.append(unit["label"])
        refresh_units()

    unit_label_field = ft.TextField(
        label="Unité (facultatif)",
        hint_text="ex : fruit, verre, part",
        width=220,
        on_change=lambda e: clear_error(unit_label_field),
    )
    unit_grams_field = ft.TextField(
        label="Poids d'une unité (g)",
        width=220,
        keyboard_type=ft.KeyboardType.NUMBER,
        on_change=lambda e: clear_error(unit_grams_field),
    )

    # --- Mode 1 : teneurs saisies à la main (pour 100 g) ---
    per100 = existing["per100"] if editing and existing.get("kind") == "manual" else {}
    value_fields = {
        n["key"]: ft.TextField(
            label=f"{n['label']} ({n['unit']})",
            value=field_value(per100.get(n["key"])),
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
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
    is_recipe = editing and existing.get("kind") == "recipe"
    ingredients: list[dict] = [dict(i) for i in existing.get("ingredients", [])] if is_recipe else []
    ing_food, ing_suggestions = make_food_input(ctx, lambda e: add_ingredient(), expand=True)
    ing_food.label = "Ingrédient"
    ing_grams = make_grams_input(ctx, lambda e: add_ingredient(), width=110)
    ingredients_col = ft.Column(spacing=0)
    total_text = ft.Text("Aucun ingrédient pour l'instant.", color=ft.Colors.GREY_700)
    recipe_error = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)
    final_weight = ft.TextField(
        label="Poids final du plat (g), facultatif",
        value=field_value(existing.get("final_weight")) if is_recipe else None,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
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
        if editing and depends_on(ctx.state["custom_foods"], food["name"], existing["name"]):
            ing_food.error = "Cet aliment contient déjà la recette : une recette ne peut pas se contenir"
            page.update()
            return
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
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
    )

    def on_mode_change(e=None):
        manual_col.visible = mode.value == "manual"
        recipe_col.visible = mode.value == "recipe"
        page.update()

    mode = ft.RadioGroup(
        value="recipe" if is_recipe else "manual",
        on_change=on_mode_change,
        content=ft.Column(
            [
                ft.Radio(value="manual", label="Saisir les nutriments"),
                ft.Radio(value="recipe", label="Recette (à partir d'autres aliments)"),
            ],
            spacing=0,
        ),
    )
    manual_col.visible = not is_recipe
    recipe_col.visible = is_recipe
    save_error = ft.Text("", color=ft.Colors.RED_700, visible=False)

    def check_unit() -> tuple[bool, str, float | None]:
        """Valide les deux champs de l'unité à ajouter : (ok, nom, grammes)."""
        unit_label = " ".join((unit_label_field.value or "").split())
        unit_grams_text = (unit_grams_field.value or "").strip()
        if not unit_label and not unit_grams_text:
            return True, "", None
        ok, unit_grams = True, None
        kept = {normalize(u["label"]) for u in units if u["label"] not in removed_units}
        if not unit_label:
            unit_label_field.error = "Donne un nom à l'unité"
            ok = False
        elif normalize(unit_label) == GRAMS_UNIT:
            unit_label_field.error = f"« {GRAMS_UNIT} » est réservé, choisis un autre nom"
            ok = False
        elif normalize(unit_label) in kept:
            unit_label_field.error = "Cette unité existe déjà"
            ok = False
        if not unit_grams_text:
            unit_grams_field.error = "Indique le nombre de grammes"
            ok = False
        else:
            unit_grams = parse_grams(unit_grams_text)
            if unit_grams is None:
                unit_grams_field.error = "Invalide"
                ok = False
        return ok, unit_label, unit_grams

    def build_food() -> dict | None:
        """L'aliment tel que saisi, ou None (erreurs affichées sous les champs)."""
        name = " ".join((name_field.value or "").split())
        ok = True
        same_name = editing and normalize(name) == normalize(existing["name"])
        if not name:
            name_field.error = "Donne un nom à l'aliment"
            ok = False
        elif normalize(name) in ctx.foods and not same_name:
            name_field.error = "Un aliment porte déjà ce nom"
            ok = False

        food: dict = {"name": name}
        if mode.value == "manual":
            values = {}
            for n in NUTRIENTS:
                value = parse_nutrient_value(value_fields[n["key"]].value or "")
                if value is None:
                    value_fields[n["key"]].error = "Invalide"
                    ok = False
                else:
                    values[n["key"]] = value
            food.update(kind="manual", per100=values)
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
        return food if ok else None

    def save(e=None):
        unit_ok, unit_label, unit_grams = check_unit()
        food = build_food()
        if food is None or not unit_ok:
            page.update()
            return
        try:
            if editing:
                ctx.update_custom_food(existing["name"], food)
                for label in removed_units:
                    ctx.remove_food_unit(food["name"], label)
            else:
                ctx.add_custom_food(food)
        except ValueError as error:  # garde-fou : les cas connus sont déjà vérifiés plus haut
            save_error.value = str(error)
            save_error.visible = True
            page.update()
            return
        if unit_label and unit_grams is not None:
            try:
                ctx.add_food_unit(food["name"], unit_label, unit_grams)
            except ValueError:
                pass  # garde-fou seulement : l'aliment est enregistré, l'unité pourra être ajoutée ensuite
        if on_saved:
            on_saved(food["name"])
        else:
            back()

    show_screen(
        ctx,
        ft.Column(
            [
                ft.Row(
                    [
                        ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Retour", on_click=lambda e: back()),
                        ft.Text(
                            "Modifier un aliment" if editing else "Ajouter un aliment",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                        ),
                    ]
                ),
                intro_text(existing, ctx.food_usage(existing["name"]) if editing else {}),
                name_field,
                *([ft.Text("Unités", weight=ft.FontWeight.W_600), units_col] if units else []),
                ft.Row([unit_label_field, unit_grams_field], wrap=True, spacing=10, run_spacing=10),
                ft.Text(
                    "Facultatif : une unité pratique pour la saisie ensuite (ex. « 1 fruit » plutôt qu'en "
                    "grammes). D'autres unités pourront être ajoutées plus tard, depuis l'accueil.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                mode,
                manual_col,
                recipe_col,
                save_error,
                ft.Row(
                    [
                        ft.TextButton("Annuler", on_click=lambda e: back()),
                        ft.FilledButton("Enregistrer" if editing else "Enregistrer l'aliment", on_click=save),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
    )
    if units:
        refresh_units()
    if ingredients:
        refresh_ingredients()
