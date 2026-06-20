# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : StatusApiToTable.py
Groupe : Status
Description : Interroge l'API TaxRef Statuts (locationId=INSEED + code département),
              une ligne par statut par espèce. Enregistre la table sans géométrie
              dans biblizou.gpkg|status_data.
"""

import time
import requests
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsMessageLog,
    Qgis
)
from qgis.PyQt.QtCore import QVariant

from .base.ApiUtils import collect_cdnom_from_config, create_taxref_session
from .base.LayerManager import LayerManager

API_BASE = "https://taxref.mnhn.fr/api/status/search/lines"
BATCH_SIZE = 50
MAX_RETRIES = 3


def _fetch_status_batch(location_id: str, taxref_ids: list, session) -> list:
    """Requête une page de statuts pour un lot de taxrefId."""
    query = f"locationId={location_id}&page=1&size=10000"
    for tid in taxref_ids:
        query += f"&taxrefId={tid}"
    full_url = f"{API_BASE}?{query}"

    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(full_url, timeout=30)
            if r.status_code == 200:
                return r.json().get("_embedded", {}).get("status", [])
            QgsMessageLog.logMessage(
                f"[StatusApiToTable]: HTTP {r.status_code} lot, tentative {attempt + 1}",
                "Biblizou", Qgis.Warning
            )
        except requests.RequestException as e:
            QgsMessageLog.logMessage(
                f"[StatusApiToTable]: Erreur requête {e}",
                "Biblizou", Qgis.Warning
            )
        time.sleep(2)
    return []


def run(gpkg_path, code_insee_dept, layer_config, progress_callback=None, log_callback=None):
    """
    Args:
        gpkg_path: chemin vers biblizou.gpkg
        code_insee_dept: code INSEE du département (ex. "07", "2A")
        layer_config: liste de dicts [{'layer_id': '...', 'column': '...'}]
        progress_callback: optional (current, total, message)
        log_callback: optional (message)
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        QgsMessageLog.logMessage(f"[StatusApiToTable]: {msg}", "Biblizou", Qgis.Info)
        if log_callback:
            log_callback(msg)

    log("Collecte des cd_nom depuis les couches...")
    cd_nom_list = collect_cdnom_from_config(layer_config)
    if not cd_nom_list:
        return False, "Aucun cd_nom trouvé dans les couches sélectionnées."

    location_id = f"INSEED{code_insee_dept}"
    log(f"Requêtage API Statuts (locationId={location_id}, {len(cd_nom_list)} taxons)...")

    session = create_taxref_session()
    all_rows = []
    total_batches = (len(cd_nom_list) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(cd_nom_list), BATCH_SIZE):
        batch = cd_nom_list[i: i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        if progress_callback:
            progress_callback(batch_num, total_batches, f"Lot {batch_num}/{total_batches}")

        for s in _fetch_status_batch(location_id, batch, session):
            taxon = s.get("taxon") or {}
            all_rows.append({
                "cdnom": str(taxon.get("id", "")),
                "scientificName": taxon.get("scientificName") or "",
                "statusTypeName": s.get("statusTypeName") or "",
                "statusTypeGroup": s.get("statusTypeGroup") or "",
                "statusCode": s.get("statusCode") or "",
                "statusName": s.get("statusName") or "",
                "locationId": s.get("locationId") or "",
                "locationName": s.get("locationName") or "",
                "statusRemarks": (s.get("statusRemarks") or "")[:500],
                "source": (s.get("source") or "")[:1000],
            })
        time.sleep(0.3)

    if not all_rows:
        return False, "Aucun statut récupéré depuis l'API."

    fields = [
        QgsField("cdnom", QVariant.String),
        QgsField("scientificName", QVariant.String),
        QgsField("statusTypeName", QVariant.String),
        QgsField("statusTypeGroup", QVariant.String),
        QgsField("statusCode", QVariant.String),
        QgsField("statusName", QVariant.String),
        QgsField("locationId", QVariant.String),
        QgsField("locationName", QVariant.String),
        QgsField("statusRemarks", QVariant.String),
        QgsField("source", QVariant.String),
    ]

    temp_layer = QgsVectorLayer("None", "status_data", "memory")
    temp_layer.dataProvider().addAttributes(fields)
    temp_layer.updateFields()

    for row in all_rows:
        feat = QgsFeature(temp_layer.fields())
        feat.setAttributes([row[f.name()] for f in temp_layer.fields()])
        temp_layer.dataProvider().addFeature(feat)

    success, err_msg = LayerManager.save_to_gpkg(temp_layer, gpkg_path)
    if not success:
        return False, f"Erreur sauvegarde GPKG : {err_msg}"

    log(f"Table status_data enregistrée : {len(all_rows)} lignes.")
    return True, f"{len(all_rows)} statuts enregistrés dans status_data."
