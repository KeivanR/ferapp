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


def make_food_input(ctx: AppContext, on_submit, **kwargs) -> tuple[ft.TextField, ft.Column]:
    """Champ « Aliment » + colonne de suggestions qui se remplit pendant la frappe."""
    suggestions = ft.Column(spacing=0)
    field = ft.TextField(label="Aliment", hint_text="ex : lentilles cuites", **kwargs)

    def pick(name: str):
        field.value = name
        field.error = None
        suggestions.controls = []
        ctx.page.update()

    def on_change(e):
        field.error = None
        matches = search_foods(field.value or "", ctx.foods)
        # Pas de suggestion si la saisie correspond déjà exactement à un aliment.
        if len(matches) == 1 and matches[0].lower() == (field.value or "").strip().lower():
            matches = []
        suggestions.controls = [suggestion_tile(ctx, m, pick) for m in matches]
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
