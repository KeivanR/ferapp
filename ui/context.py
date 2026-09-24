"""État partagé entre les écrans, construit une fois par ui/app.py.

Aucun écran ne dépend d'un autre écran directement (pas d'import du genre
`from ui.home import show_main` dans ui/profile_edit.py) : ils naviguent tous via
`ctx.router.show_xxx()`. Le routeur est rempli après coup par ui/app.py, une fois que
tous les écrans existent — voir la docstring de ui/app.py pour le détail.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Callable, Optional

import flet as ft

from nutrition import Profile, merge_foods
from nutrition import add_food_unit as _add_food_unit
from nutrition import units_for_food
from storage import save_state


@dataclass
class Router:
    """Un pointeur par écran, à appeler pour y naviguer : `ctx.router.show_main()`.

    Ajouter un écran = ajouter un attribut ici + le fichier ui/xxx.py + le brancher dans
    ui/app.py. Rien d'autre à toucher dans les écrans existants.
    """

    show_splash: Optional[Callable[[], None]] = None
    show_welcome: Optional[Callable[[], None]] = None
    show_profile: Optional[Callable[[], None]] = None
    show_profile_edit: Optional[Callable[[], None]] = None
    show_custom_food: Optional[Callable[[], None]] = None
    show_main: Optional[Callable[[], None]] = None


@dataclass
class AppContext:
    """Tout ce dont un écran a besoin. Une seule instance, créée dans ui/app.py et passée
    en argument à chaque fonction show_xxx(ctx) ; il n'y a pas d'état global ailleurs.
    """

    page: ft.Page
    state: dict  # voir storage.load_state : {"profile", "journal", "custom_foods", "food_units"}
    foods: dict[str, dict]  # base officielle + aliments personnalisés (nutrition.merge_foods)
    official_foods: dict[str, dict] = field(default_factory=dict)  # pour recalculer `foods`
    router: Router = field(default_factory=Router)

    def get_profile(self) -> Profile:
        return Profile.from_dict(self.state["profile"])

    def today_key(self) -> str:
        return datetime.date.today().isoformat()

    def entries_today(self) -> list[dict]:
        """Entrées du journal alimentaire d'aujourd'hui (liste modifiable en place)."""
        return self.state["journal"].setdefault(self.today_key(), [])

    def save(self) -> None:
        """Écrit l'état (profil, journal, aliments personnalisés) sur disque."""
        save_state(self.state)

    def add_custom_food(self, food: dict) -> None:
        """Ajoute un aliment personnalisé, sauvegarde, et remet `foods` à jour."""
        self.state["custom_foods"].append(food)
        self.save()
        self.foods.clear()
        self.foods.update(merge_foods(self.official_foods, self.state["custom_foods"]))

    def units_for(self, food_name: str) -> list[dict]:
        """Unités familières connues pour cet aliment (voir nutrition.units_for_food)."""
        return units_for_food(food_name, self.foods, self.state["food_units"])

    def add_food_unit(self, food_name: str, label: str, grams: float) -> dict:
        """Ajoute une unité pour cet aliment et sauvegarde. Peut lever ValueError (message
        affichable) si l'aliment est inconnu ou l'unité invalide — voir nutrition.add_food_unit."""
        unit = _add_food_unit(food_name, label, grams, self.foods, self.state["food_units"])
        self.save()
        return unit
