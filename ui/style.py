"""Constantes d'affichage, lues depuis config.toml (section [display]).

Regroupées ici pour que tous les écrans utilisent les mêmes couleurs/tailles ; pour changer
l'apparence, modifie config.toml plutôt que ces valeurs (voir le README).
"""

import flet as ft

from nutrition import CONFIG

COLOR_LOW = CONFIG["display"]["color_low"]  # apport bas (sous LOW_THRESHOLD)
COLOR_TODO = CONFIG["display"]["color_todo"]  # apport en cours, pas encore atteint
COLOR_DONE = CONFIG["display"]["color_done"]  # apport recommandé atteint
COLOR_CUSTOM = CONFIG["display"]["color_custom_food"]  # aliments hors base officielle
LOW_THRESHOLD = CONFIG["display"]["low_threshold"] / 100  # en fraction de l'apport recommandé
RING_SIZE = CONFIG["display"]["ring_size"]  # beaucoup de nutriments suivis
RING_SIZE_MAX = CONFIG["display"]["ring_size_max"]  # un seul nutriment suivi
RING_STROKE = CONFIG["display"]["ring_stroke_width"]
RING_ROWS_MAX = CONFIG["display"]["ring_rows_max"]  # au-delà, bande qui défile horizontalement
CHART_COLORS: list[str] = CONFIG["display"]["chart_colors"]  # une par aliment dans le détail d'un cercle
CHART_COLOR_OTHER = CONFIG["display"]["chart_color_other"]  # regroupement « Autres aliments »

# Ombre légère des cartes (fenêtre de détail d'un cercle)
CARD_SHADOW = ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK), offset=ft.Offset(0, 2))


def level_color(ratio: float) -> str:
    """Couleur d'un taux de complétion (1.0 = apport recommandé atteint) : bas, en cours ou atteint."""
    if ratio >= 1:
        return COLOR_DONE
    return COLOR_LOW if ratio < LOW_THRESHOLD else COLOR_TODO
