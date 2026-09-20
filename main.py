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
    parse_grams,
    recommended_intakes,
    search_foods,
)
from storage import load_state, save_state

FOODS = load_foods(Path(__file__).parent / "foods.csv")

COLOR_TODO = ft.Colors.ORANGE_600
COLOR_DONE = ft.Colors.GREEN_600


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

    def today_key() -> str:
        return datetime.date.today().isoformat()

    def get_profile() -> Profile:
        return Profile.from_dict(state["profile"])

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
            profile = Profile(
                age=age,
                sex=sex.value,
                pregnant=sex.value == "F" and pregnant.value,
                breastfeeding=sex.value == "F" and breastfeeding.value,
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
                            ft.Container(height=10),
                            ft.FilledButton("Enregistrer", on_click=save_profile),
                        ],
                        spacing=10,
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

        rings_row = ft.Row(wrap=True, alignment=ft.MainAxisAlignment.CENTER, spacing=6, run_spacing=16)
        entries_col = ft.Column(spacing=0)
        suggestions_col = ft.Column(spacing=0)

        food_field = ft.TextField(
            label="Aliment",
            hint_text="ex : lentilles cuites",
            expand=True,
            on_change=lambda e: update_suggestions(),
            on_submit=lambda e: add_entry(None),
        )
        grams_field = ft.TextField(
            label="Grammes",
            width=110,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda e: clear_grams_error(),
            on_submit=lambda e: add_entry(None),
        )

        def clear_grams_error():
            if grams_field.error:
                grams_field.error = None
                page.update()

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
            totals = daily_totals(entries, FOODS)
            ratios = completion(totals, recommended)
            rings_row.controls = [
                build_ring(n, ratios[n["key"]], totals[n["key"]], recommended[n["key"]])
                for n in NUTRIENTS
            ]
            entries_col.controls = [
                ft.ListTile(
                    title=ft.Text(f"{e['food']} — {fmt(e['grams'])} g"),
                    trailing=ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        tooltip="Supprimer",
                        on_click=lambda ev, i=i: delete_entry(i),
                    ),
                    dense=True,
                )
                for i, e in enumerate(entries)
            ] or [ft.Text("Rien d'ajouté pour l'instant.", color=ft.Colors.GREY_600)]
            page.update()

        def update_suggestions():
            food_field.error = None
            matches = search_foods(food_field.value or "", FOODS)
            # Pas de suggestion si la saisie correspond déjà exactement à un aliment.
            if len(matches) == 1 and matches[0].lower() == (food_field.value or "").strip().lower():
                matches = []
            suggestions_col.controls = [
                ft.ListTile(title=ft.Text(m), dense=True, on_click=lambda ev, m=m: pick(m))
                for m in matches
            ]
            page.update()

        def pick(name: str):
            food_field.value = name
            suggestions_col.controls = []
            page.update()

        def add_entry(e):
            food = find_food(food_field.value or "", FOODS)
            grams = parse_grams(grams_field.value or "")
            ok = True
            if food is None:
                food_field.error = "Choisis un aliment dans la liste"
                ok = False
            if grams is None:
                grams_field.error = "Invalide"
                ok = False
            if not ok:
                page.update()
                return
            grams_field.error = None
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
                            ft.FilledButton("Ajouter", icon=ft.Icons.ADD, on_click=add_entry),
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
