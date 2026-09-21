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

## Utilisation

- **Ajouter** : tape l'aliment (suggestions pendant la frappe) et le grammage, puis « Ajouter ».
- **Nutriment principal** : sous chaque entrée s'affiche le nutriment (parmi ceux choisis dans le profil) dont elle
  couvre la plus grande part de l'apport journalier recommandé, avec la quantité ingérée.
- **Nouvel aliment** : le bouton « Nouvel aliment » crée un aliment personnalisé, soit en saisissant ses
  teneurs pour 100 g (case vide = 0), soit comme une recette (liste d'aliments avec leurs grammages, poids final
  facultatif). Il apparaît en orange (« · perso ») et en tête des suggestions ; le nom doit être unique.
  Une recette est calculée à l'enregistrement : modifier plus tard un de ses ingrédients ne la met pas à jour.
- **Modifier** : touche une entrée (ou le crayon) pour changer l'aliment et/ou le grammage ; la poubelle la supprime.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `main.py` | Interface : page profil + page principale (saisie, cercles, liste des repas) |
| `nutrition.py` | Logique : chargement du CSV, apports de référence, calculs |
| `foods.csv` | Base Ciqual convertie (valeurs pour 100 g), générée par `build_foods.py` |
| `build_foods.py` | Convertit la table Ciqual `.xlsx` en `foods.csv` (à lancer sur ton ordinateur) |
| `foods_demo.csv` | Mini-base de 45 aliments utilisée par les tests |
| `storage.py` | Sauvegarde du profil, du journal et des aliments personnalisés (JSON local) |
| `test_nutrition.py` | Tests unitaires de la logique |

## Mettre à jour la base Ciqual

```bash
pip install openpyxl
python build_foods.py "Table Ciqual 2025_FR_2025_11_03.xlsx"
```

Colonnes de repli : vitamine B9 = équivalents folates (DFE) sinon folates totaux ; vitamine E = alpha-tocophérol sinon « vitamine E » ; vitamine D = D sinon D2 + D3.
Nettoyage : `-` = manquant (compté 0), `traces` et `< x` = 0 (choix prudent), virgules décimales converties.
Les aliments sans aucun minéral suivi renseigné sont écartés. Les vitamines A, D, E, K1, C, B9 et B12
sont aussi extraites (14 nutriments au total, choisis par l'utilisateur dans son profil).

## Ajouter un nutriment

1. Vérifie que la colonne existe dans `foods.csv` (sinon ajoute-la dans `COLUMNS` de `build_foods.py` et relance la conversion).
2. Ajoute une entrée dans `NUTRIENTS` (`nutrition.py`), avec son `group` (« Minéraux », « Vitamines »...).
3. Ajoute ses apports de référence dans `REFERENCES` (`nutrition.py`).

La case du profil et le cercle de la page principale se génèrent automatiquement.

## Avertissement

Les aliments viennent de la vraie table Ciqual, mais les apports de référence de `nutrition.py`
sont des ordres de grandeur saisis pour le prototype (inspirés EFSA/ANSES) : à vérifier avant tout usage réel.
Cette app n'est pas un dispositif médical.