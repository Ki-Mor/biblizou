# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BiblizouSettings
                                 A QGIS plugin
 Moissonnage bibliographique automatisé
                             -------------------
        begin                : 2026-09-10
        copyright            : (C) 2026 by François Botcazou
        email                : francois.botcazou@proton.me
 ***************************************************************************/
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


def sanitize_gpkg_name(name):
    """
    Nettoie un nom de GeoPackage saisi par l'utilisateur :
    - retire les caractères invalides pour un nom de fichier,
    - force l'extension .gpkg,
    - retombe sur DEFAULT_GPKG_NAME si le résultat est vide.
    """
    name = (name or "").strip()
    name = _INVALID_CHARS_RE.sub("", name)

    if not name:
        return DEFAULT_GPKG_NAME

    if not name.lower().endswith(".gpkg"):
        name += ".gpkg"

    return name


def get_gpkg_filename():
    """Retourne le nom du GeoPackage d'export configuré (ou la valeur par défaut)."""
    return QgsSettings().value(SETTINGS_KEY_GPKG_NAME, DEFAULT_GPKG_NAME)


def set_gpkg_filename(name):
    """Nettoie puis enregistre le nom du GeoPackage. Retourne le nom final enregistré."""
    clean_name = sanitize_gpkg_name(name)
    QgsSettings().setValue(SETTINGS_KEY_GPKG_NAME, clean_name)
    return clean_name
