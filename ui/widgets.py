"""Petits widgets et validations réutilisés par plusieurs écrans : formatage des nombres,
saisie d'un aliment avec suggestions, saisie d'un grammage, validation des deux ensemble.

Utilisé par ui/home.py (ajout du jour, modification d'une entrée) et ui/custom_food.py
(choix des ingrédients d'une recette).
"""

from __future__ import annotations

import flet as ft

from nutrition import GRAMS_UNIT, find_food, normalize, parse_grams, search_foods

from .context import AppContext
from .style import COLOR_CUSTOM


def fmt(value: float) -> str:
    """12.0 -> '12', 3.456 -> '3.5', 0.04 -> '0.04'."""
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.0f}" if abs(value - round(value)) < 0.05 else f"{value:.1f}"
    return f"{value:.1f}" if value >= 1 else f"{value:.2f}"


def suggestion_tile(ctx: AppContext, name: str, on_pick) -> ft.ListTile:
    """Une suggestion ; en orange si l'aliment ne vient pas de la base officielle."""
    custom = bool(ctx.foods.get(normalize(name), {}).get("custom"))
    return ft.ListTile(
        title=ft.Text(
            f"{name} · perso" if custom else name,
            color=COLOR_CUSTOM if custom else None,
            weight=ft.FontWeight.W_600 if custom else None,
        ),
        dense=True,
        on_click=lambda ev: on_pick(name),
    )


def make_food_input(
    ctx: AppContext, on_submit, on_food_changed=None, **kwargs
) -> tuple[ft.TextField, ft.Column]:
    """Champ « Aliment » + colonne de suggestions qui se remplit pendant la frappe.

    `on_food_changed(texte)`, si fourni, est rappelé à chaque changement du texte (frappe ou
    clic sur une suggestion) — utilisé par QuantityInput pour recharger les unités disponibles
    quand l'aliment saisi change.
    """
    suggestions = ft.Column(spacing=0)
    field = ft.TextField(label="Aliment", hint_text="ex : lentilles cuites", **kwargs)

    def notify():
        if on_food_changed:
            on_food_changed(field.value or "")

    def pick(name: str):
        field.value = name
        field.error = None
        suggestions.controls = []
        notify()
        ctx.page.update()

    def on_change(e):
        field.error = None
        matches = search_foods(field.value or "", ctx.foods)
        # Pas de suggestion si la saisie correspond déjà exactement à un aliment.
        if len(matches) == 1 and matches[0].lower() == (field.value or "").strip().lower():
            matches = []
        suggestions.controls = [suggestion_tile(ctx, m, pick) for m in matches]
        notify()
        ctx.page.update()

    field.on_change = on_change
    field.on_submit = on_submit
    return field, suggestions


def make_grams_input(ctx: AppContext, on_submit, **kwargs) -> ft.TextField:
    """Champ « Grammes » ; efface son erreur dès que l'utilisateur retape quelque chose."""
    field = ft.TextField(label="Grammes", keyboard_type=ft.KeyboardType.NUMBER, **kwargs)

    def on_change(e):
        if field.error:
            field.error = None
            ctx.page.update()

    field.on_change = on_change
    field.on_submit = on_submit
    return field


def validate(ctx: AppContext, food_input: ft.TextField, grams_input: ft.TextField):
    """Retourne (aliment, grammes) ou None en affichant les erreurs sous les champs."""
    food = find_food(food_input.value or "", ctx.foods)
    grams = parse_grams(grams_input.value or "")
    if food is None:
        food_input.error = "Choisis un aliment dans la liste"
    if grams is None:
        grams_input.error = "Invalide"
    if food is None or grams is None:
        ctx.page.update()
        return None
    return food, grams


def _fmt_grams(value: float) -> str:
    """150.0 -> '150', 7.5 -> '7,5', 12.345 -> '12' (affichage : virgule française, pas de faux détail)."""
    rounded = round(value) if value >= 10 else round(value, 1)
    return f"{rounded:g}".replace(".", ",")


class QuantityInput:
    """Saisie d'une quantité dans une unité familière propre à l'aliment ou en grammes, dans UNE
    seule barre : on tape le nombre dans le champ, et l'unité est affichée à droite du champ,
    avec une flèche qui déroule la liste des unités — voir nutrition.units_for_food /
    nutrition.default_unit_for / nutrition.add_food_unit.

    L'unité présélectionnée pour un aliment est la dernière utilisée pour lui, sinon son unité
    par défaut, sinon les grammes (nutrition.preferred_unit) ; `unit_label` donne l'unité choisie
    au moment de l'ajout, pour la retenir (AppContext.remember_unit).

    La liste propose toujours « Grammes », suivi des unités connues pour l'aliment actuellement
    saisi, chacune avec son équivalent (« fruit (≈ 75 g) ») : son unité par défaut
    (config/unites_par_defaut.csv) et celles que l'utilisateur a lui-même ajoutées. La dernière
    option, « + Nouvelle unité », ouvre une fenêtre pour en définir une (ce qui redéfinit aussi,
    pour cet aliment, le poids d'une unité par défaut du même nom) ; elle n'apparaît qu'une fois
    l'aliment reconnu. Sous le champ, une ligne rappelle l'équivalence utilisée (« 1 tranche ≈
    30 g », puis « 2 × 30 g = 60 g » dès qu'un nombre est tapé). Rechargé via `set_food()` à
    chaque fois que l'aliment saisi change (relie ça au `on_food_changed` de `make_food_input`).

    Usage : crée l'instance, place `quantity.control` dans la page, appelle `set_food(nom)`
    quand l'aliment change, `resolve()` pour obtenir les grammes au moment de valider, `reset()`
    après un ajout réussi. Entrée dans le champ déclenche `on_submit`.
    """

    GRAMS = GRAMS_UNIT

    def __init__(self, ctx: AppContext, on_submit=None, **count_field_kwargs):
        self.ctx = ctx
        self._food_name = ""
        self._units: list[dict] = []
        self._value = self.GRAMS  # unité choisie : GRAMS ou le label d'une unité de self._units

        self._unit_text = ft.Text(self.GRAMS)
        self.unit_menu = ft.PopupMenuButton(
            content=ft.Container(
                ft.Row([self._unit_text, ft.Icon(ft.Icons.ARROW_DROP_DOWN)], tight=True, spacing=0),
                padding=ft.Padding.only(left=8, right=8),
            ),
            items=[],
            menu_position=ft.PopupMenuPosition.UNDER,
            tooltip="Choisir l'unité",
        )
        self.count_field = ft.TextField(
            label="Quantité",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=on_submit,
            helper_max_lines=2,
            suffix_icon=self.unit_menu,
            **count_field_kwargs,
        )
        self.count_field.on_change = self._on_count_change
        self.control = self.count_field
        self._rebuild_menu()

    # --- état affiché ------------------------------------------------------------------------
    def _current_unit(self) -> dict | None:
        return next((u for u in self._units if u["label"] == self._value), None)

    def _update_display(self) -> None:
        """Unité affichée dans la barre + ligne d'aide (équivalence en grammes de l'unité choisie)."""
        unit = self._current_unit()
        self._unit_text.value = unit["label"] if unit else self.GRAMS
        if unit is None:
            self.count_field.helper = None
            return
        count = parse_grams(self.count_field.value or "")
        if count is None:
            self.count_field.helper = f"1 {unit['label']} ≈ {_fmt_grams(unit['grams'])} g"
        else:
            total = count * unit["grams"]
            self.count_field.helper = f"{_fmt_grams(count)} × {_fmt_grams(unit['grams'])} g = {_fmt_grams(total)} g"

    def _rebuild_menu(self) -> None:
        items = [ft.PopupMenuItem(content="Grammes", on_click=lambda e: self._select(self.GRAMS))]
        items += [
            ft.PopupMenuItem(
                content=f"{u['label']} (≈ {_fmt_grams(u['grams'])} g)",
                on_click=lambda e, label=u["label"]: self._select(label),
            )
            for u in self._units
        ]
        if find_food(self._food_name, self.ctx.foods) is not None:
            items.append(ft.PopupMenuItem(content="+ Nouvelle unité", on_click=lambda e: self._open_new_unit_dialog()))
        self.unit_menu.items = items
        if self._value != self.GRAMS and self._current_unit() is None:
            self._value = self.GRAMS  # unité inconnue pour ce nouvel aliment : retour aux grammes
        self._update_display()

    # --- événements -----------------------------------------------------------------------------
    def _on_count_change(self, e=None):
        changed = bool(self.count_field.error)
        self.count_field.error = None
        if self._value != self.GRAMS:
            self._update_display()
            changed = True
        if changed:
            self.ctx.page.update()

    def _select(self, label: str) -> None:
        self._value = label
        self._update_display()
        self.ctx.page.update()

    # --- API --------------------------------------------------------------------------------------
    def set_food(self, food_name: str) -> None:
        """À appeler quand l'aliment saisi change : recharge les unités connues pour ce nouvel
        aliment et présélectionne la dernière utilisée (sinon son unité par défaut)."""
        self._food_name = food_name or ""
        self._units = self.ctx.units_for(self._food_name) if self._food_name else []
        self._value = self.ctx.preferred_unit_for(self._food_name, self._units)
        self._rebuild_menu()
        self.ctx.page.update()

    @property
    def unit_label(self) -> str:
        """Unité actuellement choisie : GRAMS ou le label d'une unité familière."""
        return self._value

    def is_empty(self) -> bool:
        return not (self.count_field.value or "").strip()

    async def focus(self) -> None:
        await self.count_field.focus()

    def resolve(self) -> float | None:
        """Grammes correspondant à la saisie, ou None en affichant l'erreur sous le champ
        (comme `validate()`, ne rafraîchit pas la page elle-même : à l'appelant de le faire)."""
        count = parse_grams(self.count_field.value or "")
        if count is None:
            self.count_field.error = "Invalide"
            return None
        unit = self._current_unit()
        return count * unit["grams"] if unit else count

    def reset(self) -> None:
        """Vide la saisie après un ajout réussi (l'unité est de nouveau présélectionnée au prochain
        `set_food`)."""
        self.count_field.value = ""
        self.count_field.error = None
        self._value = self.GRAMS
        self._update_display()

    def _open_new_unit_dialog(self) -> None:
        page = self.ctx.page
        label_field = ft.TextField(label="Nom de l'unité", hint_text="ex : fruit, verre, cuillère", width=260)
        grams_field = ft.TextField(
            label="Équivaut à combien de grammes ?", keyboard_type=ft.KeyboardType.NUMBER, width=260
        )

        def clear(field: ft.TextField):
            if field.error:
                field.error = None
                page.update()

        label_field.on_change = lambda e: clear(label_field)
        grams_field.on_change = lambda e: clear(grams_field)

        def save(e=None):
            grams = parse_grams(grams_field.value or "")
            if grams is None:
                grams_field.error = "Invalide"
                page.update()
                return
            try:
                unit = self.ctx.add_food_unit(self._food_name, label_field.value or "", grams)
            except ValueError as err:
                label_field.error = str(err)
                page.update()
                return
            page.pop_dialog()
            self._units = self.ctx.units_for(self._food_name)
            self._value = unit["label"]  # sélectionne la nouvelle unité
            self._rebuild_menu()
            page.update()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Nouvelle unité"),
                content=ft.Column([label_field, grams_field], tight=True, width=260),
                scrollable=True,
                actions=[
                    ft.TextButton("Annuler", on_click=lambda e: page.pop_dialog()),
                    ft.FilledButton("Ajouter", on_click=save),
                ],
            )
        )


def validate_with_quantity(ctx: AppContext, food_input: ft.TextField, quantity: QuantityInput):
    """Comme `validate()`, mais la quantité vient d'un `QuantityInput` (grammes ou unité
    familière) plutôt que d'un champ grammes brut. Retourne (aliment, grammes) ou None."""
    food = find_food(food_input.value or "", ctx.foods)
    grams = quantity.resolve()
    if food is None:
        food_input.error = "Choisis un aliment dans la liste"
    if food is None or grams is None:
        ctx.page.update()
        return None
    return food, grams
