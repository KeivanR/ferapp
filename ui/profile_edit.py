"""Formulaire du profil : âge, sexe, situation (pour une femme) et nutriments suivis.

Accessible depuis la fiche (ui/profile_view.py) via son bouton « Modifier », ou
directement au tout premier lancement quand aucun profil n'existe encore (voir
ui/welcome.py). Le bouton « Enregistrer » est dupliqué en haut (barre fixe) et en bas,
pour ne pas avoir à redescendre après avoir coché les nutriments.
"""

from __future__ import annotations

from dataclasses import replace

import flet as ft

from nutrition import AGE_MAX, AGE_MIN, NUTRIENTS, REFERENCES, WOMAN_STATUSES, Profile

from .context import AppContext


def show_profile_edit(ctx: AppContext) -> None:
    page = ctx.page
    has_profile = bool(ctx.state.get("profile"))
    current = Profile.from_dict(ctx.state["profile"]) if has_profile else Profile()

    age_field = ft.TextField(
        label="Âge",
        value=str(current.age),
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.NumbersOnlyInputFilter(),
        width=120,
    )

    # Situation d'une femme : un seul choix parmi WOMAN_STATUSES (réglée, enceinte...).
    # Réponse enregistrée, sinon estimation d'après l'âge (config : menstruation_age_range).
    status_group = ft.RadioGroup(
        value=replace(current, sex="F").effective_status(),
        content=ft.Column(
            [ft.Radio(value=k, label=v["label"]) for k, v in WOMAN_STATUSES.items()],
            spacing=0,
        ),
    )
    # Nutriments dont la référence dépend de la situation (au moins une clé autre que « femme »).
    status_labels = [n["label"] for n in NUTRIENTS if set(REFERENCES[n["key"]]) - {"homme", "femme"}]
    female_controls: list[ft.Control] = [ft.Text("Situation"), status_group]
    if status_labels:
        female_controls.append(
            ft.Text(f"Change la référence de : {', '.join(status_labels)}", size=12, color=ft.Colors.GREY_700)
        )
    female_options = ft.Column(female_controls, visible=current.sex == "F")

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
    # Message d'erreur aussi tout en haut, pour le voir quand on enregistre depuis le haut.
    form_error = ft.Text("", color=ft.Colors.RED_700, visible=False)

    # Cases regroupées par famille (Minéraux, Vitamines, ...) dans l'ordre de config.toml
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
        if nutrient_error.visible or form_error.visible:
            nutrient_error.visible = False
            form_error.visible = False
            page.update()

    def set_all_nutrients(value: bool):
        for c in nutrient_checks.values():
            c.value = value
        nutrient_error.visible = False
        form_error.visible = False
        page.update()

    def on_sex_change(e):
        female_options.visible = sex.value == "F"
        page.update()

    sex = ft.RadioGroup(
        value=current.sex,
        on_change=on_sex_change,
        content=ft.Row([ft.Radio(value="F", label="Femme"), ft.Radio(value="H", label="Homme")]),
    )

    def fail(message: str):
        form_error.value = message
        form_error.visible = True
        page.update()

    def save_profile(e=None):
        form_error.visible = False
        try:
            age = int(age_field.value)
            if not AGE_MIN <= age <= AGE_MAX:
                raise ValueError
        except (TypeError, ValueError):
            age_field.error = f"Entre un âge valide ({AGE_MIN}-{AGE_MAX})"
            fail("Âge invalide")
            return
        chosen = [k for k, c in nutrient_checks.items() if c.value]
        if not chosen:
            nutrient_error.value = "Choisis au moins un nutriment"
            nutrient_error.visible = True
            fail("Choisis au moins un nutriment")
            return
        is_woman = sex.value == "F"
        profile = Profile(
            age=age,
            sex=sex.value,
            status=status_group.value if is_woman else None,
            nutrients=chosen,
        )
        ctx.state["profile"] = profile.to_dict()
        ctx.save()
        ctx.router.show_profile()

    def save_button() -> ft.FilledButton:
        # Un bouton en haut (barre fixe) et un en bas de la page : même action.
        return ft.FilledButton("Enregistrer", icon=ft.Icons.CHECK, on_click=save_profile)

    # Barre du haut : reste visible quand on fait défiler le formulaire.
    page.appbar = ft.AppBar(
        title=ft.Text("Ton profil", weight=ft.FontWeight.BOLD),
        center_title=False,
        leading=(
            ft.IconButton(
                ft.Icons.ARROW_BACK,
                tooltip="Retour sans enregistrer",
                on_click=lambda e: ctx.router.show_profile(),
            )
            if has_profile
            else None
        ),
        actions=[save_button(), ft.Container(width=12)],
    )
    page.clean()
    page.add(
        ft.SafeArea(
            ft.Container(
                padding=ft.Padding.only(left=20, right=20, top=4, bottom=20),
                content=ft.Column(
                    [
                        ft.Text(
                            "Il sert à calculer tes apports recommandés pour chaque nutriment.",
                            color=ft.Colors.GREY_700,
                        ),
                        form_error,
                        ft.Container(height=6),
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
                        save_button(),
                    ],
                    spacing=10,
                ),
            )
        )
    )
