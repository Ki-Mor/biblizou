# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : StatusJoinTaxref.py
Groupe : bdc
Description : Enrichit la table status_data avec nom vernaculaire et groupe taxonomique
              obtenus par requête API TaxRef (GET taxa/{cd_nom}), comme TaxrefApiToTable.
              Enregistre le résultat dans biblizou.gpkg|<layer_name>_joined (par défaut layer_name = "status_data").
"""

import time
import requests
from qgis.core import (
    QgsField,
    QgsMessageLog,
    Qgis
)

from qgis.PyQt.QtCore import QVariant

from ..base.LayerUtils import LayerUtils


API_TAXA = "https://taxref.mnhn.fr/api/taxa"
MAX_RETRIES = 2


def _fetch_taxon_info(cdnom, session):
    """Récupère vernacularName1 et groupe (classe ou ordre) via l'API TaxRef."""
    try:
        r = session.get(f"{API_TAXA}/{cdnom}", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        nom_vern = (data.get("vernacularName1") or data.get("nomVern") or "")
        if isinstance(nom_vern, dict):
            nom_vern = nom_vern.get("value", "") or ""
        groupe = (data.get("classe") or data.get("ordre") or data.get("groupe") or "")
        if isinstance(groupe, dict):
            groupe = groupe.get("value", "") or ""
        return {"nom_vern": str(nom_vern), "groupe": str(groupe)}
    except Exception:
        return None


def run(gpkg_path: str, layer_name: str = "status_data", progress_callback=None, log_callback=None) -> tuple[bool, str]:
    """
    Charge la couche layer_name (par défaut status_data) depuis gpkg_path, pour chaque cdnom
    distinct appelle l'API TaxRef pour récupérer nom vernaculaire et groupe, puis ajoute les colonnes
    nom_vern et groupe à layer_name, enregistrées dans une nouvelle couche <layer_name>_joined. Pas de jointure avec la table data_taxref.
        Args:
                gpkg_path: chemin vers biblizou.gpkg
                layer_name: layer status_data obtenue de StatusApiToTable
                progress_callback:
                log_callback: optional (message)

        Returns:
            (success: bool, message: str)
        """

    def log(msg):
        QgsMessageLog.logMessage(f"[StatusJoinTaxRef]: {msg}", "Biblizou", Qgis.Info) #mis à jour aujourd'hui précédemment QgsMessageLog.logMessage(msg, "Biblizou", level=Qgis.Info)
        if log_callback:
            log_callback(msg)

    layer_status = LayerUtils.load_from_gpkg(gpkg_path, layer_name)
    if layer_status is None:
        return False, f"Avertissement : aucune couche {layer_name} trouvée dans le GeoPackage."

    idx_cdnom = layer_status.fields().indexOf("cdnom")
    if idx_cdnom == -1:
        return False, f"Champ cdnom absent de {layer_name}."

    # Cdnom distincts
    cdnoms = set()
    for feat in layer_status.getFeatures():
        v = feat.attributes()[idx_cdnom]
        if v is not None:
            key = str(v).split(".")[0].strip()
            if key:
                cdnoms.add(key)

    if not cdnoms:
        return False, f"Aucun cdnom dans {layer_name}."

    log(f"Enrichissement via API TaxRef pour {len(cdnoms)} taxons (nom vern, groupe)...")
    session = requests.Session()
    session.headers.update({"accept": "application/hal+json;version=1"})
    taxon_info = {}
    for i, cdnom in enumerate(sorted(cdnoms)):
        if progress_callback and len(cdnoms) > 0:
            progress_callback(i + 1, len(cdnoms), f"API TaxRef {cdnom}")
        info = _fetch_taxon_info(cdnom, session)
        taxon_info[cdnom] = info or {"nom_vern": "", "groupe": ""}
        time.sleep(0.15)

    def compute_fn(feat):
       cdnom = feat.attributes()[idx_cdnom]
       key = str(cdnom).split(".")[0].strip() if cdnom is not None else ""
       info = taxon_info.get(key, {"nom_vern": "", "groupe": ""})
       return [info["nom_vern"], info["groupe"]]

    new_fields = [QgsField("nom_vern", QVariant.String), QgsField("groupe", QVariant.String)]

    layer_joined = LayerUtils.add_computed_fields(
        layer_status, new_fields, compute_fn, output_name=f"{layer_name}_joined"
    )
    if layer_joined is None:
        return False, "Avertissement : aucune référence taxonomique ajoutée."

    success, err_msg = LayerUtils.save_to_gpkg(layer_joined, gpkg_path)
    if not success:
        return False, f"Erreur sauvegarde GPKG : {err_msg}"

    log(f"Colonnes Taxref ajoutées à {layer_name}.")
    return True, f"Colonnes Taxref ajoutées à {layer_name}."

