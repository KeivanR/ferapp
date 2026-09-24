"""Petits widgets et validations réutilisés par plusieurs écrans : formatage des nombres,
saisie d'un aliment avec suggestions, saisie d'un grammage, validation des deux ensemble.

Utilisé par ui/home.py (ajout du jour, modification d'une entrée) et ui/custom_food.py
(choix des ingrédients d'une recette).
"""

from __future__ import annotations

import flet as ft

from nutrition import find_food, normalize, parse_grams, search_foods

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
    """Saisie d'une quantité en grammes ou dans une unité familière propre à l'aliment, via un
    menu déroulant — voir nutrition.units_for_food / nutrition.default_unit_for /
    nutrition.add_food_unit.

    Le menu propose toujours « Grammes », suivi des unités connues pour l'aliment actuellement
    saisi : son unité par défaut (config/unites_par_defaut.csv, ex. « fruit » pour un kiwi,
    « assiette » pour des pâtes cuites) et celles que l'utilisateur a lui-même ajoutées. La
    dernière option, « + Nouvelle unité », ouvre une fenêtre pour en définir une (ce qui
    redéfinit aussi, pour cet aliment, le poids d'une unité par défaut du même nom) ; elle
    n'apparaît qu'une fois l'aliment reconnu. Sous le champ, une ligne rappelle l'équivalence
    utilisée (« 1 tranche ≈ 30 g », puis « 2 × 30 g = 60 g » dès qu'un nombre est tapé), pour
    que l'estimation reste visible et vérifiable. Rechargé via `set_food()` à chaque fois que
    l'aliment saisi change (relie ça au `on_food_changed` de `make_food_input`).

    Usage : crée l'instance, place `quantity.control` dans la page, appelle `set_food(nom)`
    quand l'aliment change, `resolve()` pour obtenir les grammes au moment de valider, `reset()`
    après un ajout réussi.
    """

    GRAMS = "grammes"
    NEW_UNIT = "__nouvelle_unite__"  # valeur sentinelle : une action, jamais une vraie unité

    def __init__(self, ctx: AppContext, on_submit=None, **count_field_kwargs):
        self.ctx = ctx
        self._food_name = ""
        self._units: list[dict] = []
        self._last_value = self.GRAMS  # pour revenir dessus si "+ Nouvelle unité" est choisi

        self.count_field = ft.TextField(
            label="Grammes",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_submit=on_submit,
            helper_max_lines=2,
            **count_field_kwargs,
        )
        self.count_field.on_change = self._on_count_change

        self.unit_dropdown = ft.Dropdown(
            label="Unité",
            value=self.GRAMS,
            options=[ft.DropdownOption(key=self.GRAMS, text="Grammes")],
            on_select=self._on_unit_select,
            width=200,  # assez pour « cuillère à soupe » sans couper le texte
        )

        self.control = ft.Row([self.unit_dropdown, self.count_field], vertical_alignment=ft.CrossAxisAlignment.START)

    def _on_count_change(self, e=None):
        changed = bool(self.count_field.error)
        self.count_field.error = None
        if self.unit_dropdown.value != self.GRAMS:
            self._update_label()
            changed = True
        if changed:
            self.ctx.page.update()

    def _current_unit(self) -> dict | None:
        return next((u for u in self._units if u["label"] == self.unit_dropdown.value), None)

    def _update_label(self):
        """Libellé du champ + ligne d'aide qui montre l'équivalence en grammes de l'unité choisie."""
        unit = self._current_unit() if self.unit_dropdown.value != self.GRAMS else None
        if unit is None:
            self.count_field.label = "Grammes"
            self.count_field.helper = None
            return
        self.count_field.label = "Nombre"  # l'unité est rappelée juste dessous (helper)
        count = parse_grams(self.count_field.value or "")
        if count is None:
            self.count_field.helper = f"1 {unit['label']} ≈ {_fmt_grams(unit['grams'])} g"
        else:
            total = count * unit["grams"]
            self.count_field.helper = f"{_fmt_grams(count)} × {_fmt_grams(unit['grams'])} g = {_fmt_grams(total)} g"

    def _rebuild_options(self, keep_value: str) -> None:
        options = [ft.DropdownOption(key=self.GRAMS, text="Grammes")]
        options += [ft.DropdownOption(key=u["label"], text=u["label"]) for u in self._units]
        if find_food(self._food_name, self.ctx.foods) is not None:
            options.append(ft.DropdownOption(key=self.NEW_UNIT, text="+ Nouvelle unité"))
        self.unit_dropdown.options = options
        known = {self.GRAMS} | {u["label"] for u in self._units}
        self.unit_dropdown.value = keep_value if keep_value in known else self.GRAMS
        self._last_value = self.unit_dropdown.value
        self._update_label()

    def set_food(self, food_name: str) -> None:
        """À appeler quand l'aliment saisi change : recharge la suggestion et les unités connues
        pour ce nouvel aliment (et revient à « grammes » si l'unité choisie n'existe plus pour lui)."""
        self._food_name = food_name or ""
        self._units = self.ctx.units_for(self._food_name) if self._food_name else []
        self._rebuild_options(keep_value=self.unit_dropdown.value)
        self.ctx.page.update()

    def _on_unit_select(self, e=None) -> None:
        if self.unit_dropdown.value == self.NEW_UNIT:
            # "+ Nouvelle unité" est une action, pas un choix : on revient à la sélection
            # précédente pendant que la fenêtre est ouverte.
            self.unit_dropdown.value = self._last_value
            self._update_label()
            self.ctx.page.update()
            self._open_new_unit_dialog()
            return
        self._last_value = self.unit_dropdown.value
        self._update_label()
        self.ctx.page.update()

    def resolve(self) -> float | None:
        """Grammes correspondant à la saisie, ou None en affichant l'erreur sous le champ
        (comme `validate()`, ne rafraîchit pas la page elle-même : à l'appelant de le faire)."""
        count = parse_grams(self.count_field.value or "")
        if count is None:
            self.count_field.error = "Invalide"
            return None
        if self.unit_dropdown.value == self.GRAMS:
            return count
        unit = next((u for u in self._units if u["label"] == self.unit_dropdown.value), None)
        return count * unit["grams"] if unit else count  # unité disparue : repli grammes

    def reset(self) -> None:
        """Vide la saisie après un ajout réussi ; garde l'aliment et ses unités chargées."""
        self.count_field.value = ""
        self.count_field.error = None
        self.unit_dropdown.value = self.GRAMS
        self._last_value = self.GRAMS
        self._update_label()

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
            self._rebuild_options(keep_value=unit["label"])  # sélectionne la nouvelle unité
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
