"""
Auteur : François Botcazou
Nom : ApiUtils.py
Groupe : base
Description : Utilitaire pour les scripts API
"""

import requests
import re
from qgis.core import QgsProject


def collect_cdnom_from_config(layer_config: list) -> list:
    """
    Collecte les cd_nom uniques depuis les couches du projet QGIS.

    Args:
        layer_config: liste de dicts [{'layer_id': '...', 'column': '...'}]
    Returns:
        list: cd_nom uniques sous forme de strings numériques nettoyées
    """
    unique_codes = set()
    for config in layer_config:
        layer = QgsProject.instance().mapLayer(config["layer_id"])
        if not layer:
            continue
        idx = layer.fields().lookupField(config["column"])
        if idx == -1:
            continue
        for feat in layer.getFeatures():
            val = feat.attributes()[idx]
            if val is not None and str(val).strip():
                clean_val = "".join(filter(str.isdigit, str(val)))
                if clean_val:
                    unique_codes.add(clean_val)
    return list(unique_codes)

def collect_cdnom_sources(layer_config: list) -> dict:
    """Provenance des cd_nom : {colonne: {cd_nom, ...}}, une colonne par couche.
    Nom de colonne = 'src_' + nom de la couche nettoyé."""
    names = {}    # layer_id -> colonne
    sources = {}  # colonne -> codes
    for config in layer_config:
        layer = QgsProject.instance().mapLayer(config["layer_id"])
        if not layer:
            continue
        idx = layer.fields().lookupField(config["column"])
        if idx == -1:
            continue
        lid = layer.id()
        if lid not in names:
            base = "src_" + re.sub(r"\W+", "_", layer.name()).strip("_")
            col, n = base, 2
            while col in sources:
                col = f"{base}_{n}"
                n += 1
            names[lid] = col
            sources[col] = set()
        for feat in layer.getFeatures():
            val = feat.attributes()[idx]
            if val is not None and str(val).strip():
                clean_val = "".join(filter(str.isdigit, str(val)))
                if clean_val:
                    sources[names[lid]].add(clean_val)
    return sources


def create_taxref_session() -> requests.Session:
    """
    Retourne une session requests configurée pour l'API TaxRef INPN.
    Header 'accept' requis par l'API HAL+JSON.
    """
    session = requests.Session()
    session.headers.update({"accept": "application/hal+json;version=1"})
    return session
