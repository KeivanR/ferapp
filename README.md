# Nutri-Suivi (prototype)

App mobile en Python (Flet) : tu saisis ce que tu manges (aliment + grammes), l'app
additionne les minéraux et vitamines ingérés dans la journée et affiche un cercle de complétion par
nutriment (100 % = apport recommandé pour ton profil atteint).

Nécessite **Python 3.11 ou plus** (lecture de `config.toml` avec `tomllib`).

## Lancer

```bash
pip install -r requirements.txt
python main.py                # fenêtre bureau
flet run --web main.py        # dans le navigateur
flet run --android main.py    # sur ton téléphone via l'app "Flet" (Play Store / App Store)
flet build apk                # APK autonome (nécessite le SDK Flutter/Android, non testé ici)
pytest                        # tests de la logique et de la configuration
```

## Utilisation

- **Démarrage** : une page de présentation (titre, phrase d'accroche, indicateur de chargement) s'affiche
  brièvement à chaque lancement (durée réglable, `splash_seconds` dans `config.toml`). Ensuite :
  - un profil existe déjà -> la page principale s'ouvre directement ;
  - premier lancement, aucun profil enregistré -> un écran de bienvenue invite à créer son profil avant de
    proposer quoi que ce soit d'autre (bouton « Remplir mon profil »).
- **Profil** : l'icône en haut de la page principale ouvre une **fiche en lecture seule** (âge, sexe, situation,
  et l'apport recommandé de chaque nutriment suivi) — rien n'y est modifiable directement. Le bouton « Modifier »
  de cette fiche ouvre le formulaire : âge, sexe et, pour une femme, sa **situation** (un seul choix) : non réglée,
  réglée, abondamment réglée, enceinte ou allaitement. Le bouton « Enregistrer » est en haut (barre fixe, toujours
  visible) et en bas ; il ramène à la fiche. Sans réponse (nouveau profil), la situation proposée est « réglée »
  entre 12 et 50 ans (réglable dans `config.toml`), « non réglée » sinon.
- **Ajouter** : tape l'aliment (suggestions pendant la frappe) et le grammage, puis « Ajouter ».
- **Nutriment principal** : sous chaque entrée s'affiche le nutriment (parmi ceux choisis dans le profil) dont elle
  couvre la plus grande part de l'apport journalier recommandé, avec la quantité ingérée.
- **Nouvel aliment** : le bouton « Nouvel aliment » crée un aliment personnalisé, soit en saisissant ses
  teneurs pour 100 g (case vide = 0), soit comme une recette (liste d'aliments avec leurs grammages, poids final
  facultatif). Il apparaît en orange (« · perso ») et en tête des suggestions ; le nom doit être unique.
  Une recette est calculée à l'enregistrement : modifier plus tard un de ses ingrédients ne la met pas à jour.
- **Modifier** : touche une entrée (ou le crayon) pour changer l'aliment et/ou le grammage ; la poubelle la supprime.

## Configuration : `config.toml`

Tout ce qui se règle sans toucher au code est dans `config.toml` :

| Section | Contenu |
| --- | --- |
| `[app]` | titre, phrase d'accroche et durée de la page de démarrage, fichier d'aliments (`foods.csv`), nombre de suggestions affichées |
| `[profile]` | âge par défaut, âges min/max acceptés, tranche d'âge où « règles » est coché par défaut |
| `[display]` | taille et épaisseur des cercles, couleurs (cercle à compléter / complet / aliment perso) |
| `[foods_build]` | réglages de `build_foods.py` : groupe requis, traitement de `< x` et de `traces` |
| `[nutrients.<clé>]` | un bloc par nutriment : nom, unité, groupe, colonne du CSV, colonnes Ciqual, **apports de référence** |

Les références sont des tranches d'âge `[[âge_max_inclus, valeur], ...]` :

```toml
[nutrients.fer.reference]
homme = [[3, 7], [10, 11], [17, 13], [200, 11]]
femme = [[3, 7], [10, 11], [17, 13], [200, 11]]     # non réglée (et valeur de repli)
femme_regles = [[3, 7], [10, 11], [200, 16]]        # réglée (facultatif)
femme_regles_abondantes = [[3, 7], [10, 11], [200, 20]]  # abondamment réglée (facultatif)
grossesse = 16                                      # valeur unique (facultatif)
allaitement = 10                                    # valeur unique (facultatif)
```

Pour une femme, l'app prend la première clé définie pour le nutriment :

| Situation | Clés essayées dans l'ordre |
| --- | --- |
| Non réglée | `femme` |
| Réglée | `femme_regles`, `femme` |
| Abondamment réglée | `femme_regles_abondantes`, `femme_regles`, `femme` |
| Enceinte | `grossesse`, `femme` |
| Allaitement | `allaitement`, `femme` |

Un homme utilise toujours `homme`. Un nutriment qui n'a pas de valeur spécifique à une situation retombe donc sur
`femme` : il n'y a rien à renseigner pour ceux qui ne changent pas.

Le fichier est vérifié au démarrage : une faute (clé inconnue, âges dans le désordre, tranche qui s'arrête avant
`age_max`, colonne CSV en double...) donne un message qui cite le nutriment concerné, et l'app refuse de démarrer
plutôt que d'afficher de faux chiffres. Pour tester un autre fichier : `NUTRI_CONFIG=/chemin/autre.toml python main.py`.

## Organisation du code

```
nutrition_app/
├── main.py            point d'entrée (très court : délègue tout à ui/app.py)
├── config.toml         apports de référence, nutriments, affichage... (à éditer à la main)
├── config.py            lecture et validation stricte de config.toml
├── nutrition.py          logique métier : profil, aliments, calculs (testée, sans Flet)
├── storage.py             sauvegarde locale (JSON) du profil, du journal, des aliments perso
├── build_foods.py          convertit la table Ciqual .xlsx en foods.csv (à lancer à la main)
├── foods.csv                base Ciqual convertie (générée par build_foods.py)
├── foods_demo.csv             mini-base utilisée par les tests
├── test_nutrition.py           tests de nutrition.py et build_foods.py
├── test_config.py               tests de config.py
└── ui/                          interface graphique (Flet) : un fichier par écran
    ├── app.py                     assemble l'app (charge les données, relie les écrans)
    ├── context.py                   état partagé (AppContext) et routeur entre écrans
    ├── style.py                      couleurs et tailles (lues depuis config.toml)
    ├── widgets.py                     petits widgets réutilisés (saisie d'un aliment, formatage)
    ├── splash.py                      écran de démarrage
    ├── welcome.py                      écran de bienvenue (premier lancement)
    ├── profile_view.py                  fiche du profil (lecture seule)
    ├── profile_edit.py                   formulaire du profil
    ├── custom_food.py                     écran « Nouvel aliment »
    └── home.py                             page principale (saisie, cercles, journal)
```

Deux couches bien séparées : `nutrition.py` (+ `config.py`, `storage.py`, `build_foods.py`) porte toute la
logique et ne dépend pas de Flet — c'est ce que `test_nutrition.py` et `test_config.py` testent. `ui/` ne fait
que l'afficher : chaque écran est une fonction `show_xxx(ctx)` dans son propre fichier, qui ne connaît aucun
autre écran directement — pour changer d'écran, on appelle `ctx.router.show_yyy()` plutôt que d'importer la
fonction. C'est `ui/app.py` qui construit l'état partagé (`AppContext`, dans `ui/context.py`) et relie les
écrans entre eux au démarrage ; c'est le seul fichier qui les connaît tous.

**Ajouter un écran** : crée `ui/mon_ecran.py` avec une fonction `show_mon_ecran(ctx)`, ajoute
`show_mon_ecran` à la classe `Router` dans `ui/context.py`, puis branche-le dans `ui/app.py`
(`ctx.router.show_mon_ecran = lambda: show_mon_ecran(ctx)`). Les autres écrans n'ont rien à savoir de plus
pour pouvoir y naviguer (`ctx.router.show_mon_ecran()`).

**Ajouter un nutriment** : voir plus bas — ça se passe entièrement dans `config.toml`, aucun fichier de `ui/`
à toucher.

| Fichier | Rôle |
| --- | --- |
| `config.toml` | **Configuration** : références, nutriments, affichage, options (à éditer à la main) |
| `config.py` | Lecture et validation de `config.toml` |
| `main.py` | Point d'entrée Flet (délègue à `ui/app.py`) |
| `ui/` | Interface : un fichier par écran, voir l'arborescence ci-dessus |
| `nutrition.py` | Logique : chargement du CSV, apports de référence, calculs |
| `foods.csv` | Base Ciqual convertie (valeurs pour 100 g), générée par `build_foods.py` |
| `build_foods.py` | Convertit la table Ciqual `.xlsx` en `foods.csv` (à lancer sur ton ordinateur) |
| `foods_demo.csv` | Mini-base de 45 aliments utilisée par les tests |
| `storage.py` | Sauvegarde du profil, du journal et des aliments personnalisés (JSON local) |
| `test_nutrition.py` | Tests unitaires de la logique |
| `test_config.py` | Tests de la validation de `config.toml` |

## Mettre à jour la base Ciqual

```bash
pip install openpyxl
python build_foods.py "Table Ciqual 2025_FR_2025_11_03.xlsx"
```

La colonne Ciqual qui alimente chaque nutriment se règle dans `config.toml` (`ciqual = [...]`, expressions
régulières sur l'en-tête, essayées dans l'ordre ; une sous-liste = valeurs additionnées). Repli actuel :
vitamine B9 = équivalents folates (DFE) sinon folates totaux ; vitamine E = alpha-tocophérol sinon « vitamine E » ;
vitamine D = D sinon D2 + D3.
Nettoyage : `-` = manquant (compté 0), virgules décimales converties ; `traces` et `< x` = 0 par défaut
(choix prudent, modifiable dans `[foods_build]`). Les aliments sans aucun minéral renseigné sont écartés.

## Ajouter un nutriment

1. Ajoute un bloc `[nutrients.<clé>]` dans `config.toml` (nom, unité, groupe, `csv_column`, `ciqual`, références).
2. Relance `build_foods.py` pour créer la colonne dans `foods.csv`.

Aucun changement de code : la case du profil et le cercle de la page principale se génèrent automatiquement.

## Avertissement

Les aliments viennent de la vraie table Ciqual, mais les apports de référence de `config.toml`
sont des ordres de grandeur saisis pour le prototype (inspirés EFSA/ANSES) : à vérifier avant tout usage réel.
Cette app n'est pas un dispositif médical.
