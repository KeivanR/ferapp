# Nutri-Suivi (prototype)

App mobile en Python (Flet) : tu saisis ce que tu manges (aliment + grammes), l'app
additionne les minéraux ingérés dans la journée et affiche un cercle de complétion par
nutriment (100 % = apport recommandé pour ton profil atteint).

## Lancer

```bash
pip install -r requirements.txt
python main.py                # fenêtre bureau
flet run --web main.py        # dans le navigateur
flet run --android main.py    # sur ton téléphone via l'app "Flet" (Play Store / App Store)
flet build apk                # APK autonome (nécessite le SDK Flutter/Android, non testé ici)
pytest                        # tests de la logique
```

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `main.py` | Interface : page profil + page principale (saisie, cercles, liste des repas) |
| `nutrition.py` | Logique : chargement du CSV, apports de référence, calculs |
| `foods.csv` | Base Ciqual convertie (valeurs pour 100 g), générée par `build_foods.py` |
| `build_foods.py` | Convertit la table Ciqual `.xlsx` en `foods.csv` (à lancer sur ton ordinateur) |
| `foods_demo.csv` | Mini-base de 45 aliments utilisée par les tests |
| `storage.py` | Sauvegarde du profil et du journal (JSON local) |
| `test_nutrition.py` | Tests unitaires de la logique |

## Mettre à jour la base Ciqual

```bash
pip install openpyxl
python build_foods.py "Table Ciqual 2025_FR_2025_11_03.xlsx"
```

Nettoyage : `-` = manquant (compté 0), `traces` et `< x` = 0 (choix prudent), virgules décimales converties.
Les aliments sans aucun minéral suivi renseigné sont écartés. Les vitamines A, D, E, K1, C, B9, B12
sont déjà dans le CSV, prêtes à être ajoutées.

## Ajouter un nutriment (ex. vitamine A)

1. Vérifie que la colonne existe dans `foods.csv` (les vitamines y sont déjà ; sinon ajoute-la dans `COLUMNS` de `build_foods.py`).
2. Ajoute une entrée dans `NUTRIENTS` (`nutrition.py`).
3. Ajoute ses apports de référence dans `REFERENCES` (`nutrition.py`).

Les cercles se génèrent automatiquement à partir de `NUTRIENTS`.

## Avertissement

Les aliments viennent de la vraie table Ciqual, mais les apports de référence de `nutrition.py`
sont des ordres de grandeur saisis pour le prototype (inspirés EFSA/ANSES) : à vérifier avant tout usage réel.
Cette app n'est pas un dispositif médical.
