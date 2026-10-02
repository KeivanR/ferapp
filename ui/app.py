"""Assemble l'application : charge les données, crée l'état partagé (AppContext) et
branche le routeur entre écrans, puis affiche la page de démarrage.

Chaque écran vit dans son propre fichier (splash.py, welcome.py, profile_view.py,
profile_edit.py, custom_food.py, home.py, week.py, compare.py, my_foods.py, food_detail.py,
resources.py) sous la forme d'une fonction `show_xxx(ctx)` qui construit ses widgets et les
affiche avec ui/layout.show_screen. Aucun de
ces fichiers n'importe les autres : ils naviguent via `ctx.router.show_yyy()`, et c'est
uniquement ce module-ci qui connaît tous les écrans et les relie entre eux. Ça évite les
imports circulaires et ça permet de lire/modifier un écran sans avoir les autres ouverts.

Pour ajouter un écran : un nouveau fichier ui/xxx.py avec une fonction show_xxx(ctx), un
nouvel attribut dans Router (ui/context.py), et une ligne ici pour le brancher. Pour en faire
un onglet de la barre du bas, ajoute aussi une ligne dans TABS (ui/navigation.py).
"""

from __future__ import annotations

from pathlib import Path

import flet as ft

from nutrition import CONFIG, load_foods, merge_foods
from storage import load_state

from .compare import show_compare
from .context import AppContext
from .custom_food import show_custom_food
from .food_detail import show_food_detail
from .home import show_main
from .my_foods import show_my_foods
from .profile_edit import show_profile_edit
from .profile_view import show_profile
from .resources import show_resources
from .splash import show_splash
from .week import show_week
from .welcome import show_welcome

# Base Ciqual : chargée une seule fois au démarrage du process, pas à chaque session.
OFFICIAL_FOODS = load_foods(Path(__file__).parent.parent / CONFIG["app"]["foods_file"])


def run(page: ft.Page) -> None:
    """Point d'entrée appelé par Flet pour chaque session (voir main.py)."""
    page.title = CONFIG["app"]["title"]
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT
    # Textes intégrés de Flutter (calendrier, boutons Annuler/OK...) en français.
    french = ft.Locale("fr", "FR")
    page.locale_configuration = ft.LocaleConfiguration(supported_locales=[french], current_locale=french)

    state = load_state()
    ctx = AppContext(
        page=page,
        state=state,
        foods=merge_foods(OFFICIAL_FOODS, state["custom_foods"]),
        official_foods=OFFICIAL_FOODS,
    )

    # Un pointeur par écran (voir Router dans ui/context.py).
    ctx.router.show_splash = lambda: show_splash(ctx)
    ctx.router.show_welcome = lambda: show_welcome(ctx)
    ctx.router.show_profile = lambda: show_profile(ctx)
    ctx.router.show_profile_edit = lambda: show_profile_edit(ctx)
    ctx.router.show_custom_food = lambda name=None, back=None, on_saved=None: show_custom_food(
        ctx, name, back, on_saved
    )
    ctx.router.show_main = lambda day=None: show_main(ctx, day)
    ctx.router.show_week = lambda: show_week(ctx)
    ctx.router.show_compare = lambda: show_compare(ctx)
    ctx.router.show_my_foods = lambda: show_my_foods(ctx)
    ctx.router.show_food_detail = lambda name: show_food_detail(ctx, name)
    ctx.router.show_resources = lambda: show_resources(ctx)

    ctx.router.show_splash()
