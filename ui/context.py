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

import custom_foods
import journal
from nutrition import Profile, merge_foods, normalize, preferred_unit, units_for_food
from nutrition import add_food_unit as _add_food_unit
from nutrition import remember_unit as _remember_unit
from nutrition import remove_food_unit as _remove_food_unit
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
    # show_custom_food(name=None, back=None, on_saved=None) : crée un aliment perso (name=None) ou
    # modifie celui qui s'appelle `name` ; `back()` ramène à l'écran précédent (Annuler, ←, et
    # Enregistrer si `on_saved` n'est pas fourni) ; `on_saved(nom)` est appelé après Enregistrer.
    show_custom_food: Optional[Callable[..., None]] = None
    # show_main(jour) : accueil sur ce jour ; show_main() : accueil sur aujourd'hui.
    show_main: Optional[Callable[..., None]] = None
    show_week: Optional[Callable[[], None]] = None
    show_my_foods: Optional[Callable[[], None]] = None
    show_food_detail: Optional[Callable[[str], None]] = None  # fiche de l'aliment perso de ce nom
    show_resources: Optional[Callable[[], None]] = None


@dataclass
class AppContext:
    """Tout ce dont un écran a besoin. Une seule instance, créée dans ui/app.py et passée
    en argument à chaque fonction show_xxx(ctx) ; il n'y a pas d'état global ailleurs.
    """

    page: ft.Page
    state: dict  # voir storage.load_state : {"profile", "journal", "custom_foods", "food_units", "last_units"}
    foods: dict[str, dict]  # base officielle + aliments personnalisés (nutrition.merge_foods)
    official_foods: dict[str, dict] = field(default_factory=dict)  # pour recalculer `foods`
    router: Router = field(default_factory=Router)
    # Dernier jour affiché par l'accueil : les sous-écrans (profil, ajout d'un aliment) y
    # reviennent avec `ctx.router.show_main(ctx.home_day)`. None = aujourd'hui.
    home_day: Optional[datetime.date] = None

    def get_profile(self) -> Profile:
        return Profile.from_dict(self.state["profile"])

    # --- Journal : n'importe quel jour, passé compris (logique dans journal.py) ---

    def entries_for(self, day: datetime.date) -> list[dict]:
        """Entrées du journal ce jour-là (à lire seulement : pour modifier, voir ci-dessous)."""
        return journal.entries_for(self.state["journal"], day)

    def add_entry(self, day: datetime.date, food: str, grams: float) -> None:
        journal.add_entry(self.state["journal"], day, food, grams)
        self.save()

    def replace_entry(self, day: datetime.date, index: int, food: str, grams: float) -> None:
        journal.replace_entry(self.state["journal"], day, index, food, grams)
        self.save()

    def delete_entry(self, day: datetime.date, index: int) -> None:
        journal.delete_entry(self.state["journal"], day, index)
        self.save()

    def save(self) -> None:
        """Écrit l'état (profil, journal, aliments personnalisés) sur disque."""
        save_state(self.state)

    # --- Aliments personnalisés (logique dans custom_foods.py) ---
    # Chaque modification sauvegarde, puis remet `foods` à jour (même dict, partagé par les écrans).

    def custom_food(self, name: str) -> dict | None:
        """L'aliment perso de ce nom, tel qu'enregistré (avec "kind", "ingredients"...), ou None."""
        return custom_foods.find_custom(self.state["custom_foods"], name)

    def food_usage(self, name: str) -> dict:
        """{"meals": nombre de repas du journal, "recipes": [recettes qui l'utilisent]}."""
        return custom_foods.food_usage(self.state, name)

    def add_custom_food(self, food: dict) -> None:
        self.state["custom_foods"].append(food)
        self._foods_changed()

    def update_custom_food(self, old_name: str, food: dict) -> None:
        """Remplace / renomme un aliment perso (ValueError avec un message affichable si refusé)."""
        custom_foods.update_custom_food(self.state, old_name, food, self.official_foods)
        self._foods_changed()

    def delete_custom_food(self, name: str) -> None:
        """Supprime un aliment perso et ses repas (ValueError si une recette l'utilise encore)."""
        custom_foods.delete_custom_food(self.state, name)
        self._foods_changed()

    def _foods_changed(self) -> None:
        self.save()
        self.foods.clear()
        self.foods.update(merge_foods(self.official_foods, self.state["custom_foods"]))

    def units_for(self, food_name: str) -> list[dict]:
        """Unités familières connues pour cet aliment (voir nutrition.units_for_food)."""
        return units_for_food(food_name, self.foods, self.state["food_units"])

    def preferred_unit_for(self, food_name: str, units: list[dict]) -> str:
        """Unité à présélectionner pour cet aliment (voir nutrition.preferred_unit)."""
        return preferred_unit(food_name, self.foods, units, self.state["last_units"])

    def remember_unit(self, food_name: str, label: str) -> None:
        """Retient la dernière unité utilisée pour cet aliment. Ne sauvegarde pas : c'est fait
        avec l'entrée du journal qui l'accompagne (à appeler avant add_entry)."""
        _remember_unit(food_name, label, self.foods, self.state["last_units"])

    def add_food_unit(self, food_name: str, label: str, grams: float) -> dict:
        """Ajoute une unité pour cet aliment et sauvegarde. Peut lever ValueError (message
        affichable) si l'aliment est inconnu ou l'unité invalide — voir nutrition.add_food_unit."""
        unit = _add_food_unit(food_name, label, grams, self.foods, self.state["food_units"])
        self.save()
        return unit

    def remove_food_unit(self, food_name: str, label: str) -> None:
        """Retire une unité ajoutée par l'utilisateur pour cet aliment, et sauvegarde."""
        _remove_food_unit(food_name, label, self.foods, self.state["food_units"])
        self.save()

    def user_units(self, food_name: str) -> list[dict]:
        """Unités ajoutées par l'utilisateur pour cet aliment (sans l'unité par défaut du CSV)."""
        food = self.foods.get(normalize(food_name))
        return list(self.state["food_units"].get(normalize(food["name"]), [])) if food else []
