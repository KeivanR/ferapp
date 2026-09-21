"""Application mobile de suivi des carences nutritionnelles (Flet, Python pur).

Lancer sur ordinateur :   python main.py
Lancer dans le navigateur : flet run --web main.py
Construire l'APK :          flet build apk
"""

from __future__ import annotations

import datetime
from pathlib import Path

import flet as ft

from nutrition import (
    NUTRIENTS,
    Profile,
    completion,
    daily_totals,
    find_food,
    load_foods,
    merge_foods,
    normalize,
    parse_grams,
    parse_nutrient_value,
    recipe_per100,
    recommended_intakes,
    search_foods,
    selected_nutrients,
    top_nutrient,
)
from storage import load_state, save_state

OFFICIAL_FOODS = load_foods(Path(__file__).parent / "foods.csv")

COLOR_TODO = ft.Colors.ORANGE_600
COLOR_DONE = ft.Colors.GREEN_600
COLOR_CUSTOM = ft.Colors.ORANGE_800  # aliments ajoutés par l'utilisateur (hors base officielle)


def fmt(value: float) -> str:
    """12.0 -> '12', 3.456 -> '3.5', 0.04 -> '0.04'."""
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.0f}" if abs(value - round(value)) < 0.05 else f"{value:.1f}"
    return f"{value:.1f}" if value >= 1 else f"{value:.2f}"


def main(page: ft.Page):
    page.title = "Nutri-Suivi"
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT

    state = load_state()
    # Base officielle + aliments personnalisés ; modifiée sur place quand on en ajoute un.
    foods = merge_foods(OFFICIAL_FOODS, state["custom_foods"])

    def today_key() -> str:
        return datetime.date.today().isoformat()

    def get_profile() -> Profile:
        return Profile.from_dict(state["profile"])

    def suggestion_tile(name: str, on_pick) -> ft.ListTile:
        """Une suggestion ; en orange si l'aliment ne vient pas de la base officielle."""
        custom = bool(foods.get(normalize(name), {}).get("custom"))
        return ft.ListTile(
            title=ft.Text(
                f"{name} · perso" if custom else name,
                color=COLOR_CUSTOM if custom else None,
                weight=ft.FontWeight.W_600 if custom else None,
            ),
            dense=True,
            on_click=lambda ev: on_pick(name),
        )

    # Champs de saisie partagés : formulaire d'ajout, fenêtre de modification, recettes.
    def make_food_input(on_submit, **kwargs) -> tuple[ft.TextField, ft.Column]:
        """Champ « Aliment » + colonne de suggestions."""
        suggestions = ft.Column(spacing=0)
        field = ft.TextField(label="Aliment", hint_text="ex : lentilles cuites", **kwargs)

        def pick(name: str):
            field.value = name
            field.error = None
            suggestions.controls = []
            page.update()

        def on_change(e):
            field.error = None
            matches = search_foods(field.value or "", foods)
            # Pas de suggestion si la saisie correspond déjà exactement à un aliment.
            if len(matches) == 1 and matches[0].lower() == (field.value or "").strip().lower():
                matches = []
            suggestions.controls = [suggestion_tile(m, pick) for m in matches]
            page.update()

        field.on_change = on_change
        field.on_submit = on_submit
        return field, suggestions

    def make_grams_input(on_submit, **kwargs) -> ft.TextField:
        field = ft.TextField(label="Grammes", keyboard_type=ft.KeyboardType.NUMBER, **kwargs)

        def on_change(e):
            if field.error:
                field.error = None
                page.update()

        field.on_change = on_change
        field.on_submit = on_submit
        return field

    def validate(food_input: ft.TextField, grams_input: ft.TextField):
        """Retourne (aliment, grammes) ou None en affichant les erreurs sous les champs."""
        food = find_food(food_input.value or "", foods)
        grams = parse_grams(grams_input.value or "")
        if food is None:
            food_input.error = "Choisis un aliment dans la liste"
        if grams is None:
            grams_input.error = "Invalide"
        if food is None or grams is None:
            page.update()
            return None
        return food, grams

    # ------------------------------------------------------------------ #
    # Page profil
    # ------------------------------------------------------------------ #
    def show_profile():
        current = Profile.from_dict(state["profile"]) if state.get("profile") else Profile()

        age_field = ft.TextField(
            label="Âge",
            value=str(current.age),
            keyboard_type=ft.KeyboardType.NUMBER,
            input_filter=ft.NumbersOnlyInputFilter(),
            width=120,
        )
        pregnant = ft.Switch(label="Enceinte", value=current.pregnant)
        breastfeeding = ft.Switch(label="Allaitement", value=current.breastfeeding)
        female_options = ft.Column([pregnant, breastfeeding], visible=current.sex == "F")

        # Choix multiple des nutriments à suivre (un cercle par nutriment coché)
        nutrient_checks = {
            n["key"]: ft.Checkbox(
                label=f"{n['label']} ({n['unit']})",
                value=n["key"] in current.nutrients,
                on_change=lambda e: clear_nutrient_error(),
            )
            for n in NUTRIENTS
        }
        nutrient_error = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)

        # Cases regroupées par famille (Minéraux, Vitamines, ...) dans l'ordre de NUTRIENTS
        grouped_checks = ft.Column(spacing=0)
        last_group = None
        for n in NUTRIENTS:
            if n["group"] != last_group:
                last_group = n["group"]
                grouped_checks.controls.append(
                    ft.Text(last_group, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700)
                )
            grouped_checks.controls.append(nutrient_checks[n["key"]])

        def clear_nutrient_error():
            if nutrient_error.visible:
                nutrient_error.visible = False
                page.update()

        def set_all_nutrients(value: bool):
            for c in nutrient_checks.values():
                c.value = value
            nutrient_error.visible = False
            page.update()

        def on_sex_change(e):
            female_options.visible = sex.value == "F"
            page.update()

        sex = ft.RadioGroup(
            value=current.sex,
            on_change=on_sex_change,
            content=ft.Row(
                [ft.Radio(value="F", label="Femme"), ft.Radio(value="H", label="Homme")]
            ),
        )

        def save_profile(e):
            try:
                age = int(age_field.value)
                if not 1 <= age <= 120:
                    raise ValueError
            except (TypeError, ValueError):
                age_field.error = "Entre un âge valide (1-120)"
                page.update()
                return
            chosen = [k for k, c in nutrient_checks.items() if c.value]
            if not chosen:
                nutrient_error.value = "Choisis au moins un nutriment"
                nutrient_error.visible = True
                page.update()
                return
            profile = Profile(
                age=age,
                sex=sex.value,
                pregnant=sex.value == "F" and pregnant.value,
                breastfeeding=sex.value == "F" and breastfeeding.value,
                nutrients=chosen,
            )
            state["profile"] = profile.to_dict()
            save_state(state)
            show_main()

        page.clean()
        page.add(
            ft.SafeArea(
                ft.Container(
                    padding=20,
                    content=ft.Column(
                        [
                            ft.Text("Ton profil", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Il sert à calculer tes apports recommandés pour chaque nutriment.",
                                color=ft.Colors.GREY_700,
                            ),
                            ft.Container(height=10),
                            age_field,
                            ft.Text("Sexe"),
                            sex,
                            female_options,
                            ft.Divider(height=20),
                            ft.Text("Nutriments à suivre", size=18, weight=ft.FontWeight.W_600),
                            ft.Row(
                                [
                                    ft.TextButton("Tout cocher", on_click=lambda e: set_all_nutrients(True)),
                                    ft.TextButton("Tout décocher", on_click=lambda e: set_all_nutrients(False)),
                                ]
                            ),
                            grouped_checks,
                            nutrient_error,
                            ft.Container(height=10),
                            ft.FilledButton("Enregistrer", on_click=save_profile),
                        ],
                        spacing=10,
                    ),
                )
            )
        )

    # ------------------------------------------------------------------ #
    # Page « Nouvel aliment » : saisie manuelle des nutriments ou recette
    # ------------------------------------------------------------------ #
    def show_custom_food():
        def clear_error(field: ft.TextField):
            if field.error:
                field.error = None
                page.update()

        name_field = ft.TextField(
            label="Nom de l'aliment",
            hint_text="ex : soupe de lentilles maison",
            on_change=lambda e: clear_error(name_field),
        )

        # --- Mode 1 : teneurs saisies à la main (pour 100 g) ---
        value_fields = {
            n["key"]: ft.TextField(
                label=f"{n['label']} ({n['unit']})",
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
        ingredients: list[dict] = []
        ing_food, ing_suggestions = make_food_input(lambda e: add_ingredient(), expand=True)
        ing_food.label = "Ingrédient"
        ing_grams = make_grams_input(lambda e: add_ingredient(), width=110)
        ingredients_col = ft.Column(spacing=0)
        total_text = ft.Text("Aucun ingrédient pour l'instant.", color=ft.Colors.GREY_700)
        recipe_error = ft.Text("", color=ft.Colors.RED_700, size=12, visible=False)
        final_weight = ft.TextField(
            label="Poids final du plat (g), facultatif",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        final_weight.on_change = lambda e: clear_error(final_weight)

        def refresh_ingredients():
            ingredients_col.controls = [
                ft.ListTile(
                    title=ft.Text(f"{ing['food']} — {fmt(ing['grams'])} g"),
                    trailing=ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        tooltip="Retirer",
                        on_click=lambda ev, idx=idx: remove_ingredient(idx),
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
            checked = validate(ing_food, ing_grams)
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
            elif normalize(name) in foods:
                name_field.error = "Un aliment porte déjà ce nom"
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
                        per100=recipe_per100(ingredients, foods, weight),
                    )
            if not ok:
                page.update()
                return

            state["custom_foods"].append(food)
            save_state(state)
            foods.clear()
            foods.update(merge_foods(OFFICIAL_FOODS, state["custom_foods"]))
            show_main()

        page.clean()
        page.add(
            ft.SafeArea(
                ft.Container(
                    padding=ft.Padding.only(left=16, right=16, top=8, bottom=24),
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Retour", on_click=lambda e: show_main()),
                                    ft.Text("Nouvel aliment", size=24, weight=ft.FontWeight.BOLD),
                                ]
                            ),
                            ft.Text(
                                "Il apparaîtra en orange dans les suggestions : il ne vient pas de la base officielle.",
                                color=COLOR_CUSTOM,
                                size=13,
                            ),
                            name_field,
                            mode,
                            manual_col,
                            recipe_col,
                            ft.Row(
                                [
                                    ft.TextButton("Annuler", on_click=lambda e: show_main()),
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

    # ------------------------------------------------------------------ #
    # Page principale
    # ------------------------------------------------------------------ #
    def show_main():
        profile = get_profile()
        recommended = recommended_intakes(profile)
        shown = selected_nutrients(profile)

        rings_row = ft.Row(wrap=True, alignment=ft.MainAxisAlignment.CENTER, spacing=6, run_spacing=16)
        entries_col = ft.Column(spacing=0)

        food_field, suggestions_col = make_food_input(lambda e: add_entry(), expand=True)
        grams_field = make_grams_input(lambda e: add_entry(), width=110)

        def entries_today() -> list[dict]:
            return state["journal"].setdefault(today_key(), [])

        def build_ring(n: dict, ratio: float, total: float, rec: float) -> ft.Control:
            done = ratio >= 1
            color = COLOR_DONE if done else COLOR_TODO
            size = 88
            return ft.Column(
                [
                    ft.Stack(
                        [
                            ft.ProgressRing(
                                value=min(ratio, 1.0),
                                stroke_width=9,
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
                                    else ft.Text(
                                        f"{ratio * 100:.0f}%", weight=ft.FontWeight.BOLD, size=16
                                    )
                                ),
                            ),
                        ],
                        width=size,
                        height=size,
                    ),
                    ft.Text(n["label"], weight=ft.FontWeight.W_600, size=14),
                    ft.Text(
                        f"{fmt(total)} / {fmt(rec)} {n['unit']}",
                        size=11,
                        color=ft.Colors.GREY_700,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
                width=112,
            )

        def refresh():
            entries = entries_today()
            totals = daily_totals(entries, foods)
            ratios = completion(totals, recommended)
            rings_row.controls = [
                build_ring(n, ratios[n["key"]], totals[n["key"]], recommended[n["key"]])
                for n in shown
            ]
            entries_col.controls = [build_entry_tile(i, e) for i, e in enumerate(entries)] or [
                ft.Text("Rien d'ajouté pour l'instant.", color=ft.Colors.GREY_600)
            ]
            page.update()

        def build_entry_tile(i: int, e: dict) -> ft.Control:
            """Une ligne du journal : aliment, grammage et nutriment le plus apporté."""
            top = top_nutrient(e, foods, recommended, shown)
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
                        ft.IconButton(
                            ft.Icons.EDIT_OUTLINED,
                            tooltip="Modifier",
                            on_click=lambda ev, i=i: open_edit(i),
                        ),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE,
                            tooltip="Supprimer",
                            on_click=lambda ev, i=i: delete_entry(i),
                        ),
                    ],
                    tight=True,
                    spacing=0,
                ),
                on_click=lambda ev, i=i: open_edit(i),
            )

        def add_entry(e=None):
            checked = validate(food_field, grams_field)
            if checked is None:
                return
            food, grams = checked
            entries_today().append({"food": food["name"], "grams": grams})
            save_state(state)
            food_field.value = ""
            grams_field.value = ""
            suggestions_col.controls = []
            refresh()

        def delete_entry(index: int):
            entries = entries_today()
            if 0 <= index < len(entries):
                entries.pop(index)
                save_state(state)
                refresh()

        def open_edit(index: int):
            """Fenêtre pour corriger l'aliment et/ou le grammage d'une entrée du jour."""
            entries = entries_today()
            if not 0 <= index < len(entries):
                return
            entry = entries[index]

            edit_food, edit_suggestions = make_food_input(lambda e: save_edit(), width=300)
            edit_food.value = entry["food"]
            edit_grams = make_grams_input(lambda e: save_edit(), width=300)
            edit_grams.value = f"{entry['grams']:g}"

            def save_edit(e=None):
                checked = validate(edit_food, edit_grams)
                if checked is None:
                    return
                food, grams = checked
                entries[index] = {"food": food["name"], "grams": grams}
                save_state(state)
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
                                            ft.Text(
                                                datetime.date.today().strftime("%d/%m/%Y"),
                                                color=ft.Colors.GREY_700,
                                            ),
                                        ],
                                        spacing=0,
                                    ),
                                    ft.IconButton(
                                        ft.Icons.PERSON_OUTLINE,
                                        tooltip="Modifier mon profil",
                                        on_click=lambda e: show_profile(),
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
                                        on_click=lambda e: show_custom_food(),
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

    # ------------------------------------------------------------------ #
    if state.get("profile"):
        show_main()
    else:
        show_profile()


if __name__ == "__main__":
    ft.run(main)