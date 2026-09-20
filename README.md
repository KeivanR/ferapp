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
| `foods.csv` | Base d'aliments (valeurs pour 100 g) — à éditer à la main |
| `storage.py` | Sauvegarde du profil et du journal (JSON local) |
| `test_nutrition.py` | Tests unitaires de la logique |

## Modifier la base d'aliments

Ajoute une ligne à `foods.csv` (séparateur virgule, valeurs pour 100 g, point décimal).
Colonnes : `aliment,fer_mg,calcium_mg,magnesium_mg,zinc_mg,potassium_mg,iode_ug,selenium_ug`.

## Ajouter un nutriment (ex. vitamine A)

1. Ajoute une colonne `vitamine_a_ug` dans `foods.csv`.
2. Ajoute une entrée dans `NUTRIENTS` (`nutrition.py`).
3. Ajoute ses apports de référence dans `REFERENCES` (`nutrition.py`).

Les cercles se génèrent automatiquement à partir de `NUTRIENTS`.

## Avertissement

Les valeurs de `foods.csv` et les apports de référence de `nutrition.py` sont des ordres de
grandeur saisis pour le prototype (inspirés des tables Ciqual et des références
EFSA/ANSES) : à vérifier et à remplacer par les vraies tables avant tout usage réel.
Cette app n'est pas un dispositif médical.
