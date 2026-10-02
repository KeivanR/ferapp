"""Onglet « Mes aliments » : la liste de tous les aliments perso créés, et un bouton pour en créer
un nouveau. Toucher un aliment ouvre sa fiche (ui/food_detail.py) : sa recette, ses teneurs, et
c'est de là qu'on le modifie ou le supprime.
"""

from __future__ import annotations

from typing import Callable

import flet as ft

from nutrition import normalize

from .context import AppContext
from .layout import screen_title, show_screen
from .style import COLOR_CUSTOM, MY_FOODS_SEARCH_MIN
from .widgets import fmt, plural


def food_summary(ctx: AppContext, food: dict) -> str:
    """Sous-titre d'un aliment : type, unités, et combien de fois il a été noté."""
    if food.get("kind") == "recipe":
        parts = ["Recette, " + plural(len(food.get("ingredients", [])), "ingrédient")]
    else:
        parts = ["Nutriments saisis à la main"]
    units = ctx.user_units(food["name"])
    if units:
        parts.append(", ".join(f"1 {u['label']} = {fmt(u['grams'])} g" for u in units))
    meals = ctx.food_usage(food["name"])["meals"]
    parts.append(f"noté {meals} fois" if meals else "jamais noté")
    return " · ".join(parts)


def food_tile(ctx: AppContext, food: dict, on_open: Callable[[], None]) -> ft.Control:
    """Une ligne de la liste : icône, nom (en orange, comme dans les suggestions) et résumé.
    La toucher ouvre la fiche de l'aliment."""
    is_recipe = food.get("kind") == "recipe"
    return ft.ListTile(
        leading=ft.Icon(ft.Icons.MENU_BOOK_OUTLINED if is_recipe else ft.Icons.EGG_OUTLINED, color=COLOR_CUSTOM),
        title=ft.Text(food["name"], color=COLOR_CUSTOM, weight=ft.FontWeight.W_600),
        subtitle=ft.Text(food_summary(ctx, food), size=12, color=ft.Colors.GREY_700),
        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_600),
        on_click=lambda e: on_open(),
    )


def show_my_foods(ctx: AppContext) -> None:
    foods = sorted(ctx.state["custom_foods"], key=lambda f: normalize(f["name"]))
    list_col = ft.Column(spacing=0)

    def create(e=None) -> None:
        ctx.router.show_custom_food(back=ctx.router.show_my_foods)

    def refresh(query: str = "") -> None:
        words = normalize(query).split()
        shown = [f for f in foods if all(w in normalize(f["name"]) for w in words)]
        list_col.controls = [
            food_tile(ctx, f, on_open=lambda f=f: ctx.router.show_food_detail(f["name"])) for f in shown
        ] or [ft.Text("Aucun aliment ne correspond à ta recherche.", color=ft.Colors.GREY_600)]
        ctx.page.update()

    new_button = ft.FilledButton("Nouvel aliment", icon=ft.Icons.ADD, on_click=create)
    if foods:
        subtitle = f"{plural(len(foods), 'aliment')} créé{'s' if len(foods) > 1 else ''}"
        content: list[ft.Control] = [
            ft.Text(
                "Les aliments que tu as ajoutés, en orange dans les suggestions. Touche-en un pour voir "
                "sa recette et ses nutriments, le modifier ou le supprimer.",
                color=ft.Colors.GREY_700,
            ),
            ft.Row([new_button]),
        ]
        if len(foods) >= MY_FOODS_SEARCH_MIN:
            content.append(
                ft.TextField(
                    hint_text="Rechercher dans mes aliments",
                    prefix_icon=ft.Icons.SEARCH,
                    on_change=lambda e: refresh(e.control.value or ""),
                )
            )
        content.append(list_col)
    else:
        subtitle = None
        content = [
            ft.Container(height=24),
            ft.Icon(ft.Icons.NO_FOOD_OUTLINED, size=48, color=ft.Colors.GREY_500),
            ft.Text("Tu n'as pas encore créé d'aliment.", size=16, weight=ft.FontWeight.W_600),
            ft.Text(
                "Un aliment manque dans la liste ? Crée-le en saisissant ses nutriments, ou comme une recette "
                "faite d'autres aliments. Il apparaîtra ici.",
                color=ft.Colors.GREY_700,
                text_align=ft.TextAlign.CENTER,
            ),
            new_button,
        ]

    show_screen(
        ctx,
        ft.Column(
            [
                screen_title("Mes aliments", subtitle),
                ft.Column(
                    content,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH if foods else ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
        ),
        tab="aliments",
    )
    if foods:
        refresh()
