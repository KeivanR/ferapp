# Nutri-Suivi (prototype)

App mobile en Python (Flet) : tu saisis ce que tu manges (aliment + grammes), l'app
additionne les minéraux et vitamines ingérés dans la journée et affiche un cercle de complétion par
nutriment (100 % = apport recommandé pour ton profil atteint).

Nécessite **Python 3.11 ou plus** (lecture de `config/config.toml` avec `tomllib`).

## Lancer

```bash
pip install -r requirements.txt
python main.py                # fenêtre bureau
flet run --web main.py        # dans le navigateur
flet run --android main.py    # sur ton téléphone via l'app "Flet" (Play Store / App Store)
flet build apk                # APK autonome (nécessite le SDK Flutter/Android, non testé ici)
pytest                        # tests (dossier tests/, à lancer depuis la racine du projet)
ruff check . && ruff format . # vérifie le code et le remet en forme (pip install ruff ; réglages dans pyproject.toml)
```

## Utilisation

- **Démarrage** : une page de présentation (titre, phrase d'accroche, indicateur de chargement) s'affiche
  brièvement à chaque lancement (durée réglable, `splash_seconds` dans `config/config.toml`). Ensuite :
  - un profil existe déjà -> la page principale s'ouvre directement ;
  - premier lancement, aucun profil enregistré -> un écran de bienvenue invite à créer son profil avant de
    proposer quoi que ce soit d'autre (bouton « Remplir mon profil »).
- **Barre du bas** : trois onglets, toujours accessibles une fois le profil créé :
  - **Accueil** : la page du jour (cercles, saisie des repas, repas du jour) ;
  - **Semaine** : un tableau des nutriments suivis (lignes) jour par jour du lundi au dimanche (colonnes). Chaque
    case donne la part de l'apport recommandé atteinte ce jour-là (coche verte = atteint, « – » = rien noté) et
    chaque ligne sa moyenne sur les jours notés. Pour revoir les semaines passées, fais glisser le tableau vers la
    droite (vers la gauche pour revenir), au doigt, à la souris ou au pavé tactile : le tableau suit le geste
    puis se cale sur une semaine entière, du lundi au dimanche. Les flèches en haut font le même glissement.
    Toucher une case remplie ouvre le détail du nutriment pour ce jour-là, comme un cercle de l'accueil ;
  - **Ressources** : des liens utiles (carence en fer, recommandations alimentaires, sources des données) et une
    FAQ dépliable, question par question. Tout ce contenu est dans `config/ressources.toml`.
- **Profil** : l'icône en haut de la page principale ouvre une **fiche en lecture seule** (âge, sexe, situation,
  et l'apport recommandé de chaque nutriment suivi) — rien n'y est modifiable directement. Le bouton « Modifier »
  de cette fiche ouvre le formulaire : âge, sexe et, pour une femme, sa **situation** (un seul choix) : non réglée,
  réglée, abondamment réglée, enceinte ou allaitement. Le bouton « Enregistrer » est en haut (barre fixe, toujours
  visible) et en bas ; il ramène à la fiche. Sans réponse (nouveau profil), la situation proposée est « réglée »
  entre 12 et 50 ans (réglable dans `config.toml`), « non réglée » sinon.
- **Cercles de complétion** : juste sous le titre, un cercle par nutriment suivi (orange, vert avec une coche une
  fois l'apport recommandé atteint). Jusqu'à 6 nutriments suivis, ils forment une grille centrée ; au-delà, ils
  restent sur 2 lignes (`ring_rows_max`) et on fait glisser la bande vers la gauche pour voir les autres — les
  premiers de la liste sont toujours visibles, et le repas du jour reste à l'écran. Leur taille dépend du nombre de
  nutriments suivis : un seul -> un très grand cercle (`ring_size_max`), beaucoup -> des cercles plus petits
  (jusqu'au minimum `ring_size`).
- **Détail d'un nutriment** : toucher un cercle (ou une case de l'onglet Semaine) l'ouvre en grand, par-dessus la page floutée. Sa barre de
  progression y est découpée en segments de couleur, un par aliment du jour, proportionnels à ce que chacun
  apporte ; la liste en dessous donne pour chaque couleur l'aliment, la quantité apportée et la part de l'apport
  recommandé. Au-delà de 7 aliments, les plus petits apports sont regroupés en « Autres aliments » (gris).
  Toucher en dehors de la carte, ou la croix, la ferme.
- **Saisir un repas** : tape l'aliment (suggestions pendant la frappe — tes aliments personnalisés en tête, puis le
  ou les « aliment moyen » correspondants s'il y en a, ex. « Pain (aliment moyen) » en tapant « pain », puis les noms
  les plus courts), puis la quantité dans la barre « Quantité » et appuie sur **Entrée** : l'aliment est ajouté au
  repas du jour (il n'y a pas de bouton de validation). La barre « Quantité » n'apparaît qu'une fois un aliment
  choisi (clic sur une suggestion, ou Entrée dans le champ aliment, qui prend la 1re suggestion) et disparaît après l'ajout.
  La barre « Quantité » affiche à droite l'unité utilisée ; la petite flèche déroule la liste des unités, chacune
  avec son équivalent (« fruit (≈ 75 g) »). L'unité présélectionnée est celle que tu as utilisée la dernière fois pour cet
  aliment (grammes compris) ; pour un aliment jamais saisi, c'est son unité par défaut (pas les grammes). « Grammes » est toujours proposé ; à côté,
  **chaque aliment Ciqual a une unité par défaut** (« fruit » pour un kiwi, « tranche » pour du jambon, « verre »
  pour du lait, « cuillère à soupe » pour de l'huile, « assiette » pour des pâtes cuites...), avec son équivalent
  estimé en grammes (voir « Unités par défaut » plus bas). Une fois l'unité choisie, une ligne sous le champ
  rappelle l'équivalence utilisée (« 1 tranche ≈ 45 g », puis « 2 × 45 g = 90 g »). La dernière option du menu,
  « + Nouvelle unité », ouvre une fenêtre pour en définir une soi-même pour cet aliment (un nom et son équivalent
  en grammes, mémorisés et proposés à chaque fois que tu le retaperas) — en reprenant le nom de l'unité par défaut,
  on corrige son poids pour soi (ex. « fruit » = 100 g si tes kiwis sont gros).
- **Nutriment principal** : sous chaque entrée s'affiche le nutriment (parmi ceux choisis dans le profil) dont elle
  couvre la plus grande part de l'apport journalier recommandé, avec la quantité ingérée.
- **Ajouter** (aliment absent de la liste) : le bouton « Ajouter », sous la quantité, ouvre l'écran « Ajouter un
  aliment », qui explique en quelques mots à quoi il sert. On y crée un aliment personnalisé, soit en saisissant ses
  teneurs pour 100 g (case vide = 0), soit comme une recette (liste d'aliments avec leurs grammages, poids final
  facultatif). Il apparaît en orange (« · perso ») et en tête des suggestions ; le nom doit être unique.
  Une recette est calculée à l'enregistrement : modifier plus tard un de ses ingrédients ne la met pas à jour.
  Deux champs facultatifs permettent d'y définir tout de suite une première unité familière (ex. « part » = 250 g) ;
  d'autres pourront être ajoutées plus tard depuis l'écran principal. Les ingrédients d'une recette, eux, se
  saisissent toujours en grammes (pas d'unité à ce niveau).
- **Modifier** : touche une entrée (ou le crayon) pour changer l'aliment et/ou le grammage — toujours en grammes à
  la modification, pour ne pas avoir à deviner dans quelle unité la quantité d'origine avait été saisie ; la
  poubelle supprime l'entrée.

## Configuration : dossier `config/`

Tout ce qui se règle sans toucher au code est dans `config/` : `config.toml` (tableau ci-dessous),
`unites_par_defaut.csv` (l'unité par défaut de chaque aliment, voir « Unités par défaut ») et `ressources.toml`
(liens et FAQ de l'onglet « Ressources », voir « Modifier les ressources et la FAQ »).

| Section | Contenu |
| --- | --- |
| `[app]` | titre, phrase d'accroche et durée de la page de démarrage, fichier d'aliments (`foods.csv`), nombre de suggestions affichées |
| `[profile]` | âge par défaut, âges min/max acceptés, tranche d'âge où « règles » est coché par défaut |
| `[display]` | taille et épaisseur des cercles, nombre maximal de lignes de cercles (`ring_rows_max`), couleurs (en cours / atteint / aliment perso), seuil « apport bas » de l'onglet Semaine (`low_threshold`, en %, et `color_low`), couleurs des aliments dans le détail d'un cercle (`chart_colors`, `chart_color_other`) |
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
├── config.py           lecture et validation stricte des fichiers de config/
├── nutrition.py         logique métier : profil, aliments, unités, calculs (testée, sans Flet)
├── history.py           calculs sur plusieurs jours pour l'onglet « Semaine » (testés, sans Flet)
├── storage.py            sauvegarde locale (JSON) du profil, du journal, des aliments perso
├── build_foods.py         convertit la table Ciqual .xlsx en foods.csv (à lancer à la main)
├── foods.csv               base Ciqual convertie (générée par build_foods.py)
├── pyproject.toml          dépendances, nom de l'app pour « flet build », réglages de pytest
├── .gitignore              fichiers à ne pas versionner (caches, données perso data/, builds, .xlsx...)
├── config/                 fichiers de réglages, à éditer à la main
│   ├── config.toml           apports de référence, nutriments, affichage...
│   ├── unites_par_defaut.csv  unité familière par défaut de chaque aliment (+ son poids en grammes)
│   └── ressources.toml       liens utiles et FAQ de l'onglet « Ressources »
├── tests/                  tests automatiques (lancer « pytest » depuis la racine)
│   ├── test_nutrition.py     tests de nutrition.py et build_foods.py
│   ├── test_config.py        tests de config.py
│   ├── test_history.py       tests de history.py
│   ├── test_navigation.py    cohérence des onglets de la barre du bas
│   └── foods_demo.csv        mini-base utilisée par les tests
└── ui/                          interface graphique (Flet) : un fichier par écran
    ├── app.py                     assemble l'app (charge les données, relie les écrans)
    ├── context.py                   état partagé (AppContext) et routeur entre écrans
    ├── style.py                      couleurs et tailles (lues depuis config.toml)
    ├── layout.py                     show_screen() : affiche un écran (barres du haut et du bas, marges) ;
    │                                  show_popup() : une carte par-dessus la page floutée
    ├── navigation.py                 barre du bas : la liste des onglets (TABS)
    ├── widgets.py                     petits widgets réutilisés (saisie d'un aliment, d'une quantité en
    │                                  grammes ou en unité familière, formatage)
    ├── splash.py                      écran de démarrage
    ├── welcome.py                      écran de bienvenue (premier lancement)
    ├── profile_view.py                  fiche du profil (lecture seule)
    ├── profile_edit.py                   formulaire du profil
    ├── custom_food.py                     écran « Ajouter un aliment »
    ├── home.py                             onglet Accueil (saisie, cercles, journal)
    ├── rings.py                            cercles de l'accueil (grille, grand cercle à segments)
    ├── nutrient_detail.py                  détail d'un nutriment pour un jour (cercle agrandi, part de chaque aliment)
    ├── week.py                             onglet Semaine (taux jour par jour)
    └── resources.py                        onglet Ressources (liens, FAQ)
```

Deux couches bien séparées : `nutrition.py` et `history.py` (+ `config.py`, `storage.py`, `build_foods.py`)
portent toute la logique et ne dépendent pas de Flet — c'est ce que testent les fichiers de `tests/`. `ui/` ne fait
que l'afficher : chaque écran est une fonction `show_xxx(ctx)` dans son propre fichier, qui construit son contenu
puis l'affiche avec `show_screen(ctx, contenu, ...)` (`ui/layout.py`). Aucun écran ne connaît un
autre écran directement — pour changer d'écran, on appelle `ctx.router.show_yyy()` plutôt que d'importer la
fonction. C'est `ui/app.py` qui construit l'état partagé (`AppContext`, dans `ui/context.py`) et relie les
écrans entre eux au démarrage ; c'est le seul fichier qui les connaît tous.

**Ajouter un écran** : crée `ui/mon_ecran.py` avec une fonction `show_mon_ecran(ctx)` qui termine par
`show_screen(ctx, contenu)`, ajoute `show_mon_ecran` à la classe `Router` dans `ui/context.py`, puis branche-le
dans `ui/app.py` (`ctx.router.show_mon_ecran = lambda: show_mon_ecran(ctx)`). Les autres écrans n'ont rien à
savoir de plus pour pouvoir y naviguer (`ctx.router.show_mon_ecran()`).

**Ajouter un onglet à la barre du bas** : même chose, avec `show_screen(ctx, contenu, tab="mon_onglet")`, plus
une ligne dans `TABS` (`ui/navigation.py`) : clé, libellé, icônes, et nom de l'écran dans le Router. L'ordre de
`TABS` est l'ordre des onglets ; `tests/test_navigation.py` vérifie que chaque onglet mène bien à un écran.

**Ajouter un nutriment** : voir plus bas — ça se passe entièrement dans `config.toml`, aucun fichier de `ui/`
à toucher.

| Fichier | Rôle |
| --- | --- |
| `config/config.toml` | **Configuration** : références, nutriments, affichage, options (à éditer à la main) |
| `config/unites_par_defaut.csv` | **Unité par défaut** de chaque aliment et son poids en grammes (à éditer à la main ou dans un tableur) |
| `config.py` | Lecture et validation des fichiers de `config/` |
| `main.py` | Point d'entrée Flet (délègue à `ui/app.py`) |
| `ui/` | Interface : un fichier par écran, voir l'arborescence ci-dessus |
| `nutrition.py` | Logique : chargement du CSV, apports de référence, calculs |
| `history.py` | Logique sur plusieurs jours : semaines, taux par jour, moyennes (onglet « Semaine ») |
| `config/ressources.toml` | **Contenu de l'onglet Ressources** : liens utiles et FAQ (à éditer à la main) |
| `foods.csv` | Base Ciqual convertie (valeurs pour 100 g), générée par `build_foods.py` |
| `build_foods.py` | Convertit la table Ciqual `.xlsx` en `foods.csv` (à lancer sur ton ordinateur) |
| `tests/foods_demo.csv` | Mini-base de 45 aliments utilisée par les tests |
| `storage.py` | Sauvegarde du profil, du journal, des aliments personnalisés et des unités familières (JSON local) |
| `tests/test_nutrition.py` | Tests unitaires de la logique |
| `tests/test_config.py` | Tests de la validation des fichiers de `config/` |
| `tests/test_history.py` | Tests des calculs de l'onglet « Semaine » |
| `tests/test_navigation.py` | Vérifie que chaque onglet de la barre du bas mène à un écran existant |
| `.gitignore` | Ce que git doit ignorer : caches Python/pytest, `data/` (tes données perso quand tu lances l'app en local), sorties de `flet build`, table Ciqual `.xlsx`, archives `.zip` |

## Mettre à jour la base Ciqual

```bash
pip install openpyxl
python build_foods.py "Table Ciqual 2025_FR_2025_11_03.xlsx"
```

La colonne Ciqual qui alimente chaque nutriment se règle dans `config/config.toml` (`ciqual = [...]`, expressions
régulières sur l'en-tête, essayées dans l'ordre ; une sous-liste = valeurs additionnées). Repli actuel :
vitamine B9 = équivalents folates (DFE) sinon folates totaux ; vitamine E = alpha-tocophérol sinon « vitamine E » ;
vitamine D = D sinon D2 + D3.
Nettoyage : `-` = manquant (compté 0), virgules décimales converties ; `traces` et `< x` = 0 par défaut
(choix prudent, modifiable dans `[foods_build]`). Les aliments sans aucun minéral renseigné sont écartés.
À la fin, le script liste les aliments qui n'ont pas encore d'unité par défaut dans `config/unites_par_defaut.csv`
(les nouveautés d'une mise à jour Ciqual) : ajoute-leur une ligne (ils restent utilisables en grammes en attendant).

## Ajouter un nutriment

1. Ajoute un bloc `[nutrients.<clé>]` dans `config/config.toml` (nom, unité, groupe, `csv_column`, `ciqual`, références).
2. Relance `build_foods.py` pour créer la colonne dans `foods.csv`.

Aucun changement de code : la case du profil et le cercle de la page principale se génèrent automatiquement.

## Unités par défaut

`config/unites_par_defaut.csv` donne, pour **chacun des 2 874 aliments de `foods.csv`**, une unité familière et son
poids en grammes. Il s'ouvre dans n'importe quel tableur (encodage UTF-8, séparateur virgule) :

```csv
alim_code,aliment,unite,grammes
13021,"Kiwi, chair sans peau, avec pépins, cru",fruit,75
28900,"Jambon cuit, supérieur",tranche,45
9811,"Pâtes sèches, standard, cuites, sans sel ajouté",assiette,250
```

- `alim_code` relie la ligne à l'aliment (c'est le code Ciqual, repris dans `foods.csv`) ; `aliment` n'est là que
  pour s'y retrouver.
- Les grammes sont ceux de la **partie comestible, dans l'état décrit par le nom** (cru, cuit, égoutté...), comme les
  teneurs Ciqual : « fruit » = 75 g pour un kiwi épluché, « portion crue » = 80 g pour des pâtes sèches, « boîte » =
  105 g de thon égoutté.
- Pour qu'un aliment n'ait **pas** d'unité (seulement les grammes), laisse `unite` et `grammes` vides.
- Le fichier est vérifié au démarrage (code en double, grammes non numériques ou nuls, unité nommée « grammes »...),
  avec le numéro de la ligne fautive ; un test vérifie aussi que chaque aliment de `foods.csv` y figure.

**D'où viennent ces valeurs ?** Aucune table publique ne donne une unité ménagère pour chaque aliment Ciqual ; ce
sont donc des **estimations** : une unité par sous-groupe Ciqual (ex. « verre » 200 g pour les jus, « pot » 125 g
pour les yaourts, « portion » 30 g pour les fromages), affinée aliment par aliment là où c'était nécessaire
(kiwi 75 g, pomme 150 g, tranche de jambon cru 15 g, œuf 50 g, carré de chocolat 5 g, steak haché 100 g cru /
75 g cuit...), à partir des tailles de portions et des conditionnements courants en France, puis relues une à une.
Ce sont de bons ordres de grandeur, pas des pesées : la ligne d'aide sous le champ affiche toujours l'équivalence
utilisée, « + Nouvelle unité » permet de la corriger pour soi dans l'app, et une valeur fausse se corrige
définitivement dans ce fichier (aucun code à toucher).

## Modifier les ressources et la FAQ

L'onglet « Ressources » affiche, dans l'ordre, les blocs de `config/ressources.toml` :

```toml
[[links]]
group = "Carence en fer"            # rubrique : les liens d'une même rubrique sont regroupés
title = "Anémie par carence en fer (ameli.fr)"
url = "https://www.ameli.fr/assure/sante/themes/anemie-par-carence-en-fer"
description = "Une phrase d'explication (facultatif)."

[[faq]]
question = "Où sont enregistrées mes données ?"
answer = "Uniquement sur ton appareil."
```

Pour ajouter une question ou un lien, copie un bloc et modifie-le ; aucun code à toucher. Le fichier est vérifié
au démarrage (clé manquante ou inconnue, lien qui ne commence pas par `http://` ou `https://`...), avec un message
qui indique le bloc fautif.

## Avertissement

Les aliments viennent de la vraie table Ciqual, mais les apports de référence de `config/config.toml`
sont des ordres de grandeur saisis pour le prototype (inspirés EFSA/ANSES), et les unités par défaut sont des
estimations : à vérifier avant tout usage réel.
Cette app n'est pas un dispositif médical.
