"""Sauvegarde locale du profil et du journal alimentaire dans un fichier JSON.

Sur mobile, Flet fournit un dossier de données persistant via la variable
d'environnement FLET_APP_STORAGE_DATA ; sur ordinateur on utilise ./data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _data_file() -> Path:
    base = os.environ.get("FLET_APP_STORAGE_DATA") or str(Path(__file__).parent / "data")
    Path(base).mkdir(parents=True, exist_ok=True)
    return Path(base) / "state.json"


def load_state() -> dict:
    """{"profile": {...} | None, "journal": {"YYYY-MM-DD": [{"food": str, "grams": float}]}}"""
    try:
        return json.loads(_data_file().read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"profile": None, "journal": {}}


def save_state(state: dict) -> None:
    _data_file().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
