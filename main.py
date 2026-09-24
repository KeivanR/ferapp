"""Point d'entrée de l'application (Flet, Python pur).

Lancer sur ordinateur :     python main.py
Lancer dans le navigateur : flet run --web main.py
Construire l'APK :          flet build apk

Organisation du code (voir README.md pour le détail de chaque fichier) :
  config/, config.py         réglages, apports de référence et unités par défaut (édités à la main,
                             validés au démarrage)
  nutrition.py, storage.py   logique métier et sauvegarde locale (testées, sans dépendance à Flet)
  build_foods.py             génère foods.csv à partir de la table Ciqual (à lancer à la main)
  ui/                        interface graphique : un fichier par écran, voir ui/app.py
  tests/                     tests automatiques (lancer « pytest » depuis la racine)
"""

from __future__ import annotations

import flet as ft

from ui.app import run


def main(page: ft.Page) -> None:
    run(page)


if __name__ == "__main__":
    ft.run(main)
