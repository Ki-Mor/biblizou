# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : biblizou_settings.py
Groupe : Options
Description : Centralise la lecture/écriture des réglages généraux du plugin
              (QgsSettings), pour éviter de disperser les clés et valeurs
              par défaut dans chaque module.
"""

import re
from qgis.core import QgsSettings

SETTINGS_KEY_GPKG_NAME = "biblizou/gpkg_name"
DEFAULT_GPKG_NAME = "biblizou.gpkg"

# Caractères interdits dans un nom de fichier (Windows étant le plus restrictif)
_INVALID_CHARS_RE = re.compile(r'[\\/:*?"<>|]')

# État par défaut des checkbox (checked/unchecked) statuts dans biblizou_dialog_patri
DEFAULT_BERNE = False
DEFAULT_CITES = False
DEFAULT_BONN = False
DEFAULT_DH2 = True
DEFAULT_DH4 = False
DEFAULT_DO1 = True
DEFAULT_DO4 = False
DEFAULT_PN = True
DEFAULT_PR = True
DEFAULT_ZDET = True
DEFAULT_LR_MOND = []
DEFAULT_LR_EURO = []
DEFAULT_LR_NAT = ["NT", "VU", "EN", "CR"]
DEFAULT_LR_REG = ["NT", "VU", "EN", "CR"]


def get_invalid_chars(name):
    """
    Retourne l'ensemble des caractères interdits présents dans `name`
    (ensemble vide si le nom est valide). Utilisable tel quel pour
    construire le message de l'info-bulle plus tard.
    """
    return set(_INVALID_CHARS_RE.findall(name or ""))


def is_valid_gpkg_name(name):
    """Un nom est valide s'il n'est pas vide (une fois nettoyé des espaces) et ne contient aucun caractère interdit."""
    name = (name or "").strip()
    if not name:
        return False
    return not get_invalid_chars(name)


def get_gpkg_filename():
    """Retourne le nom du GeoPackage d'export configuré (ou la valeur par défaut)."""
    return QgsSettings().value(SETTINGS_KEY_GPKG_NAME, DEFAULT_GPKG_NAME)


def set_gpkg_filename(name):
    """Nettoie puis enregistre le nom du GeoPackage. Retourne le nom final enregistré."""
    clean_name = get_gpkg_filename()
    QgsSettings().setValue(SETTINGS_KEY_GPKG_NAME, clean_name)
    return clean_name


def get_status_bool(key: str, default_val: bool) -> bool:
    """Récupère une valeur booléenne dans QgsSettings."""
    settings = QgsSettings()
    val = settings.value(f"biblizou/{key}", None)
    if val is None:
        return default_val
    # QgsSettings peut renvoyer un booléen ou une chaîne 'true'/'false'
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes")


def set_status_bool(key: str, value: bool) -> None:
    """Enregistre un booléen dans QgsSettings."""
    settings = QgsSettings()
    settings.setValue(f"biblizou/{key}", bool(value))


def get_lr_statuts(key: str, default_list: list) -> list:
    """Récupère la liste des statuts enregistrés ou retourne la valeur par défaut."""
    settings = QgsSettings()
    val = settings.value(f"biblizou/{key}", None)
    if val is None:
        return default_list
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()]
    return list(val)


def set_lr_statuts(key: str, statuts: list) -> None:
    """Enregistre la liste des statuts sous forme de chaîne de caractères."""
    settings = QgsSettings()
    settings.setValue(f"biblizou/{key}", ",".join(statuts))
