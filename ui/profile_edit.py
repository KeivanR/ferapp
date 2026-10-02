"""Formulaire du profil : âge, sexe, situation (pour une femme) et nutriments suivis.

Accessible depuis la fiche (ui/profile_view.py) via son bouton « Modifier », ou directement au
tout premier lancement quand aucun profil n'existe encore (voir ui/welcome.py).

Les nutriments se choisissent par pastilles, rangées dans une carte par groupe (Minéraux,
Vitamines...) : on voit tout d'un coup d'œil, on touche une pastille pour la cocher ou la
décocher, et chaque carte a son bouton « Tout cocher / Tout décocher » et son compteur. Le
bouton « Enregistrer » est en haut (barre fixe, toujours visible) et en bas.
"""

from __future__ import annotations

from dataclasses import replace

import flet as ft

from nutrition import AGE_MAX, AGE_MIN, GROUPS, NUTRIENTS, REFERENCES, WOMAN_STATUSES, Profile

from .context import AppContext
from .layout import card, show_screen
from .widgets import group_icon, icon_badge

CHIP_SPACING = 6


def show_profile_edit(ctx: AppContext) -> None:
    page = ctx.page
    has_profile = bool(ctx.state.get("profile"))
    current = Profile.from_dict(ctx.state["profile"]) if has_profile else Profile()

    # Message d'erreur tout en haut, visible quand on enregistre depuis la barre du haut.
    form_error = ft.Text("", color=ft.Colors.RED_700, visible=False)

    def clear_error() -> None:
        form_error.visible = False
        nutrient_error.visible = False

    def fail(message: str) -> None:
        form_error.value = message
        form_error.visible = True
        page.update()

    # --- Toi : âge, sexe, situation ---------------------------------------------------------
    age_field = ft.TextField(
        label="Âge",
        value=str(current.age),
        suffix=ft.Text("ans"),
        keyboard_type=ft.KeyboardType.NUMBER,
        input_filter=ft.NumbersOnlyInputFilter(),
        width=110,
    )

    def on_sex_change(e) -> None:
        female_options.visible = "F" in sex.selected
        page.update()

    sex = ft.SegmentedButton(
        segments=[ft.Segment(value="F", label=ft.Text("Femme")), ft.Segment(value="H", label=ft.Text("Homme"))],
        selected=[current.sex],
        show_selected_icon=False,
        on_change=on_sex_change,
    )

    # Situation d'une femme : un seul choix parmi WOMAN_STATUSES (réglée, enceinte...).
    # Réponse enregistrée, sinon estimation d'après l'âge (config : menstruation_age_range).
    status = {"value": replace(current, sex="F").effective_status()}

    def choose_status(key: str) -> None:
        status["value"] = key
        for k, chip in status_chips.items():
            chip.selected = k == key
        page.update()

    status_chips = {
        k: ft.Chip(
            label=ft.Text(v["label"]),
            selected=k == status["value"],
            show_checkmark=False,
            on_select=lambda e, k=k: choose_status(k),
        )
        for k, v in WOMAN_STATUSES.items()
    }
    # Nutriments dont le repère dépend de la situation (au moins une clé autre que « femme »).
    status_labels = [n["label"] for n in NUTRIENTS if set(REFERENCES.get(n["key"], {})) - {"homme", "femme"}]
    female_controls: list[ft.Control] = [
        ft.Text("Situation", weight=ft.FontWeight.W_600),
        ft.Row(list(status_chips.values()), wrap=True, spacing=CHIP_SPACING, run_spacing=0),
    ]
    if status_labels:
        female_controls.append(
            ft.Text(f"Change le repère de : {', '.join(status_labels)}.", size=12, color=ft.Colors.GREY_700)
        )
    female_options = ft.Column(female_controls, spacing=6, visible=current.sex == "F")

    identity = card(
        ft.Column(
            [
                ft.Row(
                    [icon_badge(ft.Icons.PERSON), ft.Text("Toi", size=16, weight=ft.FontWeight.W_600)],
                    spacing=12,
                ),
                ft.Row([age_field, sex], spacing=12, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                female_options,
            ],
            spacing=14,
        )
    )

    # --- Nutriments à suivre : une carte par groupe, une pastille par nutriment ----------------
    chosen: set[str] = set(current.nutrients)
    by_group = {g["name"]: [n for n in NUTRIENTS if n["group"] == g["name"]] for g in GROUPS}
    chips: dict[str, ft.Chip] = {}
    group_counts = {name: ft.Text(size=12, color=ft.Colors.GREY_700) for name in by_group}
    group_toggles = {name: ft.TextButton() for name in by_group}
    total_count = ft.Text(color=ft.Colors.GREY_700)
    nutrient_error = ft.Text("Choisis au moins un nutriment", color=ft.Colors.RED_700, size=12, visible=False)

    def refresh_counts() -> None:
        """Met à jour les pastilles, les compteurs et les boutons « Tout cocher / décocher »."""
        for key, chip in chips.items():
            chip.selected = key in chosen
        for name, nutrients in by_group.items():
            count = sum(n["key"] in chosen for n in nutrients)
            group_counts[name].value = f"{count} sur {len(nutrients)}"
            group_toggles[name].content = "Tout décocher" if count == len(nutrients) else "Tout cocher"
        total_count.value = f"{len(chosen)} sur {len(NUTRIENTS)} suivis"
        clear_error()
        page.update()

    def toggle(key: str) -> None:
        chosen.symmetric_difference_update({key})
        refresh_counts()

    def set_many(keys: list[str], selected: bool) -> None:
        if selected:
            chosen.update(keys)
        else:
            chosen.difference_update(keys)
        refresh_counts()

    def toggle_group(name: str) -> None:
        keys = [n["key"] for n in by_group[name]]
        set_many(keys, selected=not all(k in chosen for k in keys))

    def group_card(group: dict) -> ft.Control:
        name = group["name"]
        for n in by_group[name]:
            chips[n["key"]] = ft.Chip(
                label=ft.Text(n["label"]),
                selected=n["key"] in chosen,
                on_select=lambda e, k=n["key"]: toggle(k),
            )
        group_toggles[name].on_click = lambda e: toggle_group(name)
        title: list[ft.Control] = [ft.Text(name, size=16, weight=ft.FontWeight.W_600)]
        if group["description"]:
            title.append(ft.Text(group["description"], size=12, color=ft.Colors.GREY_700))
        return card(
            ft.Column(
                [
                    ft.Row(
                        [icon_badge(group_icon(group)), ft.Column(title, spacing=0, expand=True)],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                    ft.Row([chips[n["key"]] for n in by_group[name]], wrap=True, spacing=CHIP_SPACING, run_spacing=0),
                    ft.Row(
                        [group_counts[name], group_toggles[name]],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=8,
            )
        )

    group_cards = [group_card(g) for g in GROUPS]

    # --- Enregistrement ---------------------------------------------------------------------
    def save_profile(e=None) -> None:
        clear_error()
        try:
            age = int(age_field.value)
            if not AGE_MIN <= age <= AGE_MAX:
                raise ValueError
        except (TypeError, ValueError):
            age_field.error = f"Entre {AGE_MIN} et {AGE_MAX}"
            fail("Âge invalide")
            return
        if not chosen:
            nutrient_error.visible = True
            fail("Choisis au moins un nutriment")
            return
        is_woman = "F" in sex.selected
        profile = Profile(
            age=age,
            sex="F" if is_woman else "H",
            status=status["value"] if is_woman else None,
            nutrients=[n["key"] for n in NUTRIENTS if n["key"] in chosen],  # dans l'ordre de config.toml
        )
        ctx.state["profile"] = profile.to_dict()
        ctx.save()
        ctx.router.show_profile()

    def save_button() -> ft.FilledButton:
        # Un bouton en haut (barre fixe) et un en bas de la page : même action.
        return ft.FilledButton("Enregistrer", icon=ft.Icons.CHECK, on_click=save_profile)

    # Barre du haut : reste visible quand on fait défiler le formulaire.
    appbar = ft.AppBar(
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
    all_keys = [n["key"] for n in NUTRIENTS]
    show_screen(
        ctx,
        ft.Column(
            [
                ft.Text("Il sert à calculer tes repères journaliers pour chaque nutriment.", color=ft.Colors.GREY_700),
                form_error,
                identity,
                ft.Container(height=4),
                ft.Row(
                    [ft.Text("Nutriments à suivre", size=18, weight=ft.FontWeight.W_600, expand=True), total_count],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
                ft.Text(
                    "Touche un nutriment pour le suivre ou l'arrêter. Chaque nutriment suivi a son cercle sur "
                    "l'accueil et sa ligne dans la semaine : mieux vaut en choisir peu, ceux qui comptent pour toi.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                *group_cards,
                ft.Row(
                    [
                        ft.TextButton("Tout cocher", on_click=lambda e: set_many(all_keys, True)),
                        ft.TextButton("Tout décocher", on_click=lambda e: set_many(all_keys, False)),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                nutrient_error,
                ft.Row([save_button()], alignment=ft.MainAxisAlignment.END),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        appbar=appbar,
    )
    refresh_counts()
