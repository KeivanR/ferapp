"""Constantes d'affichage, lues depuis config.toml (section [display]).

Regroupées ici pour que tous les écrans utilisent les mêmes couleurs/tailles ; pour changer
l'apparence, modifie config.toml plutôt que ces valeurs (voir le README).
"""

from nutrition import CONFIG

COLOR_TODO = CONFIG["display"]["color_todo"]  # cercle pas encore complet
COLOR_DONE = CONFIG["display"]["color_done"]  # cercle complet, référence atteinte
COLOR_CUSTOM = CONFIG["display"]["color_custom_food"]  # aliments hors base officielle
RING_SIZE = CONFIG["display"]["ring_size"]
RING_STROKE = CONFIG["display"]["ring_stroke_width"]
