"""Fiche d'un aliment perso, ouverte en le touchant dans l'onglet Mes aliments : sa recette (ou
« nutriments saisis à la main »), ses unités, ses teneurs pour 100 g et où il sert. Lecture
seule : c'est d'ici qu'on passe à la modification (ui/custom_food.py) ou à la suppression.

La suppression demande confirmation : elle retire aussi l'aliment des repas où il est noté, et
elle est refusée tant qu'une recette l'utilise (logique dans custom_foods.py).
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from nutrition import NUTRIENTS

from .context import AppContext
from .layout import show_screen
from .style import COLOR_CUSTOM
from .widgets import fmt, plural


def section_title(text: str) -> ft.Control:
    return ft.Text(text, size=18, weight=ft.FontWeight.W_600)


def value_row(label: str, value: str, muted: bool = False) -> ft.Control:
    """Une ligne « libellé ........ valeur »."""
    color = ft.Colors.GREY_500 if muted else None
    return ft.Row([ft.Text(label, expand=True, color=color), ft.Text(value, color=color)], spacing=12)


def recipe_section(food: dict) -> list[ft.Control]:
    """La recette : ingrédients et grammages, poids total, poids final du plat s'il a été précisé."""
    ingredients = food.get("ingredients", [])
    total = sum(i["grams"] for i in ingredients)
    rows = [value_row(i["food"], f"{fmt(i['grams'])} g") for i in ingredients]
    weights = [ft.Text(f"Poids total des ingrédients : {fmt(total)} g", size=12, color=ft.Colors.GREY_700)]
    if food.get("final_weight"):
        weights.append(
            ft.Text(f"Poids final du plat : {fmt(food['final_weight'])} g", size=12, color=ft.Colors.GREY_700)
        )
    return [section_title("Recette"), ft.Column(rows, spacing=6), *weights]


def nutrients_section(food: dict) -> list[ft.Control]:
    """Teneurs pour 100 g, par groupe ; les nutriments absents (0) sont grisés."""
    controls: list[ft.Control] = [section_title("Pour 100 g")]
    for group in dict.fromkeys(n["group"] for n in NUTRIENTS):
        controls.append(ft.Text(group, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_700))
        rows = []
        for n in (n for n in NUTRIENTS if n["group"] == group):
            amount = food["per100"].get(n["key"], 0.0)
            rows.append(value_row(n["label"], f"{fmt(amount)} {n['unit']}" if amount else "–", muted=not amount))
        controls.append(ft.Column(rows, spacing=4))
    return controls


def usage_text(usage: dict) -> str:
    """« Noté 3 fois dans tes repas. Utilisé dans la recette : Bol du matin. »"""
    text = f"Noté {usage['meals']} fois dans tes repas." if usage["meals"] else "Jamais noté dans tes repas."
    if usage["recipes"]:
        word = "les recettes" if len(usage["recipes"]) > 1 else "la recette"
        text += f" Utilisé dans {word} : {', '.join(usage['recipes'])}."
    return text


def confirm_delete(ctx: AppContext, food: dict, on_deleted: Callable[[], None]) -> None:
    """Fenêtre de confirmation avant de supprimer `food` ; explique ce qui sera supprimé avec lui,
    ou pourquoi ce n'est pas possible (une recette l'utilise)."""
    page, name = ctx.page, food["name"]
    usage = ctx.food_usage(name)

    if usage["recipes"]:
        listed = ", ".join(f"« {r} »" for r in usage["recipes"])
        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Suppression impossible"),
                content=ft.Text(
                    f"« {name} » est utilisé dans {listed}. Retire-le d'abord de cette recette, ou supprime la recette."
                ),
                actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())],
            )
        )
        return

    def delete(e=None):
        ctx.delete_custom_food(name)
        page.pop_dialog()
        on_deleted()

    where = "du repas" if usage["meals"] == 1 else "des " + plural(usage["meals"], "repas")
    consequence = f" Il sera aussi retiré {where} où il est noté." if usage["meals"] else ""
    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Supprimer « {name} » ?"),
            content=ft.Text("Cette action est définitive." + consequence),
            actions=[
                ft.TextButton("Annuler", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Supprimer", style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700), on_click=delete),
            ],
        )
    )


def show_food_detail(ctx: AppContext, name: str) -> None:
    food = ctx.custom_food(name)
    if food is None:  # supprimé entre-temps : retour à la liste
        ctx.router.show_my_foods()
        return
    is_recipe = food.get("kind") == "recipe"
    units = ctx.user_units(food["name"])

    def edit(e=None) -> None:
        # Annuler revient à cette fiche ; Enregistrer aussi, sous le nouveau nom s'il a changé.
        ctx.router.show_custom_food(
            name=food["name"],
            back=lambda: ctx.router.show_food_detail(food["name"]),
            on_saved=ctx.router.show_food_detail,
        )

    def delete(e=None) -> None:
        confirm_delete(ctx, food, on_deleted=ctx.router.show_my_foods)

    kind = (
        "Recette, " + plural(len(food.get("ingredients", [])), "ingrédient")
        if is_recipe
        else "Nutriments saisis à la main"
    )
    body: list[ft.Control] = [
        ft.Row(
            [
                ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Retour", on_click=lambda e: ctx.router.show_my_foods()),
                ft.Text(food["name"], size=24, weight=ft.FontWeight.BOLD, color=COLOR_CUSTOM, expand=True),
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
        ft.Text(kind, color=ft.Colors.GREY_700),
        ft.Text(usage_text(ctx.food_usage(food["name"])), size=12, color=ft.Colors.GREY_700),
        ft.Row(
            [
                ft.FilledButton("Modifier", icon=ft.Icons.EDIT, on_click=edit),
                ft.OutlinedButton("Supprimer", icon=ft.Icons.DELETE_OUTLINE, on_click=delete),
            ],
            spacing=10,
        ),
        ft.Divider(height=16),
    ]
    if is_recipe:
        body += [*recipe_section(food), ft.Divider(height=16)]
    if units:
        body += [
            section_title("Unités"),
            ft.Column([value_row(f"1 {u['label']}", f"{fmt(u['grams'])} g") for u in units], spacing=6),
            ft.Divider(height=16),
        ]
    body += nutrients_section(food)
    show_screen(ctx, ft.Column(body, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
