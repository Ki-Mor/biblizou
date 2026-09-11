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
