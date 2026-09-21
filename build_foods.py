"""Convertit la table Ciqual (xlsx) en foods.csv léger, prêt à être chargé par l'app.

Usage :  python build_foods.py "Table Ciqual 2025_FR_2025_11_03.xlsx" [foods.csv]
Nécessite : pip install openpyxl   (uniquement sur ton ordinateur, pas dans l'app)

Règles de nettoyage des valeurs Ciqual (par 100 g) :
  - "-" ou cellule vide  -> valeur manquante (case vide dans le CSV, comptée 0 par l'app)
  - "traces"             -> 0
  - "< 0,25"             -> 0 (choix prudent : on ne surestime pas les apports)
  - "2,45"               -> 2.45 (virgule décimale française)
"""

from __future__ import annotations

import csv
import re
import sys
import warnings
from pathlib import Path

import openpyxl

# clé CSV -> alternatives, essayées dans l'ordre : la première qui a une valeur l'emporte.
# Une alternative est une expression régulière sur l'en-tête Ciqual nettoyé (retours à la ligne
# -> espaces), ou un tuple d'expressions dont les valeurs sont additionnées (ex. D2 + D3).
COLUMNS = {
    "fer_mg": [r"^Fer \(mg"],
    "calcium_mg": [r"^Calcium \(mg"],
    "magnesium_mg": [r"^Magnésium \(mg"],
    "zinc_mg": [r"^Zinc \(mg"],
    "potassium_mg": [r"^Potassium \(mg"],
    "iode_ug": [r"^Iode \(µg"],
    "selenium_ug": [r"^Sélénium \(µg"],
    "vitamine_a_ug": [r"^Activité vitaminique A"],
    "vitamine_d_ug": [r"^Vitamine D \(µg", (r"^Vitamine D2 \(", r"^Vitamine D3 \(")],
    # alpha-tocophérol et "vitamine E" sont renseignés pour des aliments différents
    "vitamine_e_mg": [r"^Alpha-tocophérol \(vitamine E\)", r"^Vitamine E \(mg"],
    "vitamine_k1_ug": [r"^Vitamine K1 \(µg"],
    "vitamine_c_mg": [r"^Vitamine C \(mg"],
    # équivalents folates (DFE, comme la référence EFSA) d'abord, sinon folates totaux
    "vitamine_b9_ug": [r"^Vitamine B9 ou Folates totaux, équivalents folates", r"^Vitamine B9 ou Folates totaux \(µg"],
    "vitamine_b12_ug": [r"^Vitamine B12 \(µg"],
}
MINERALS = list(COLUMNS)[:7]  # colonnes utilisées par l'app aujourd'hui


def parse_value(raw) -> float | None:
    """Valeur Ciqual -> float, ou None si manquante."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = " ".join(str(raw).split()).lower()
    if text in ("", "-"):
        return None
    if text == "traces" or text.startswith("<"):
        return 0.0
    return float(text.replace(",", "."))


def resolve(row, alternatives: list[list[int]]) -> float | None:
    """Première alternative ayant une valeur ; plusieurs colonnes dans une alternative = somme."""
    for cols in alternatives:
        parts = [v for v in (parse_value(row[c]) for c in cols) if v is not None]
        if parts:
            return sum(parts)
    return None


def clean_header(h) -> str:
    return " ".join(str(h or "").split())


def convert(xlsx_path: str | Path, csv_path: str | Path) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avertissement inoffensif sur l'en-tête/pied de page
        wb = openpyxl.load_workbook(xlsx_path, read_only=True)
        rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    headers = [clean_header(h) for h in rows[0]]

    def find_col(pattern: str) -> int:
        found = [i for i, h in enumerate(headers) if re.search(pattern, h)]
        if len(found) != 1:
            raise SystemExit(f"{len(found)} colonnes pour {pattern!r} (attendu : 1)")
        return found[0]

    # clé -> liste d'alternatives, chacune = liste d'index de colonnes (plusieurs = somme)
    idx = {
        key: [[find_col(p) for p in ((alt,) if isinstance(alt, str) else alt)] for alt in alts]
        for key, alts in COLUMNS.items()
    }
    name_i = headers.index("alim_nom_fr")
    code_i = headers.index("alim_code")

    kept = dropped = 0
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["alim_code", "aliment", *COLUMNS])
        for r in rows[1:]:
            name = (r[name_i] or "").strip()
            values = [resolve(r, idx[k]) for k in COLUMNS]
            # Inutile si aucun minéral suivi n'est renseigné.
            if not name or all(v is None for v in values[: len(MINERALS)]):
                dropped += 1
                continue
            w.writerow([r[code_i], name, *("" if v is None else f"{v:g}" for v in values)])
            kept += 1
    return {"kept": kept, "dropped": dropped}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    out = sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "foods.csv"
    print(convert(sys.argv[1], out), "->", out)