"""Réglages de l'interface, lus depuis config/config.toml (sections [display] et [app]).

Regroupés ici pour que tous les écrans utilisent les mêmes valeurs. Règle du projet : tout ce
qu'on peut vouloir régler sans toucher au code (couleurs, tailles, durées, seuils, limites) est
dans config.toml, validé au démarrage par config.py, et les écrans le lisent ici. Seules les
cotes de mise en page propres à un écran (hauteur d'une ligne, marge...) restent dans son fichier.
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

# Glissement du calendrier de l'onglet Semaine
SWIPE_SWITCH_FRACTION = CONFIG["display"]["swipe_switch_fraction"]  # part de la largeur pour changer de page
SWIPE_SWITCH_SPEED = CONFIG["display"]["swipe_switch_speed"]  # px/s : un geste rapide suffit
SWIPE_SNAP_MS = CONFIG["display"]["swipe_snap_ms"]  # calage sur une page entière au relâchement
WEEK_ARROW_MS = CONFIG["display"]["week_arrow_ms"]  # glissement déclenché par les flèches

# Limites ([app])
HISTORY_YEARS = CONFIG["app"]["history_years"]  # le calendrier de l'accueil remonte jusque-là
WEEKS_MIN = CONFIG["app"]["weeks_min"]  # semaines consultables au minimum (onglet Semaine)
MY_FOODS_SEARCH_MIN = CONFIG["app"]["my_foods_search_min"]  # la recherche apparaît à partir de là

# Ombre légère des cartes (fenêtre de détail d'un cercle)
CARD_SHADOW = ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK), offset=ft.Offset(0, 2))


def level_color(ratio: float) -> str:
    """Couleur d'un taux de complétion (1.0 = apport recommandé atteint) : bas, en cours ou atteint."""
    if ratio >= 1:
        return COLOR_DONE
    return COLOR_LOW if ratio < LOW_THRESHOLD else COLOR_TODO
