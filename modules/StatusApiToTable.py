# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : StatusApiToTable.py
Groupe : Status
Description : Interroge l'API TaxRef Statuts (locationId=INSEED + code département),
              une ligne par statut par espèce. Enregistre la table sans géométrie
              dans biblizou.gpkg|status_data.
"""

import os
import time
import requests
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsMessageLog,
    QgsVectorFileWriter,
    Qgis
)
from qgis.PyQt.QtCore import QVariant

API_BASE = "https://taxref.mnhn.fr/api/status/search/lines"
BATCH_SIZE = 50
MAX_RETRIES = 3


def collect_cdnom_from_config(layer_config):
    """Collecte les cd_nom uniques depuis les couches du projet (comme TaxrefApiToTable)."""
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
                str_val = str(val).split(".")[0]
                clean_val = "".join(filter(str.isdigit, str(val)))
                if clean_val:
                    unique_codes.add(clean_val)
    return list(unique_codes)


def fetch_status_batch(location_id, taxref_ids, session):
    """Requête une page de statuts pour un lot de taxrefId."""
    params = {"locationId": location_id, "page": 1, "size": 10000}
    for tid in taxref_ids:
        params.setdefault("taxrefId", []).append(tid)
    # requests attend une liste pour taxrefId multiple du même nom
    url = API_BASE
    # Construction URL: ?locationId=INSEED07&page=1&size=10000&taxrefId=1&taxrefId=2...
    query = f"locationId={location_id}&page=1&size=10000"
    for tid in taxref_ids:
        query += f"&taxrefId={tid}"
    full_url = f"{url}?{query}"
    for attempt in range(MAX_RETRIES):
        try:
            r = session.get(full_url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                return data.get("_embedded", {}).get("status", [])
            QgsMessageLog.logMessage(
                f"StatusApiToTable: HTTP {r.status_code} pour lot, tentative {attempt + 1}",
                "Biblizou",
                level=Qgis.Warning
            )
        except requests.RequestException as e:
            QgsMessageLog.logMessage(
                f"StatusApiToTable: Erreur requête {e}",
                "Biblizou",
                level=Qgis.Warning
            )
        time.sleep(2)
    return []


def run(gpkg_path, code_insee_dept, layer_config, progress_callback=None, log_callback=None):
    """
    Point d'entrée principal.
    
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
        QgsMessageLog.logMessage(msg, "Biblizou", level=Qgis.Info)
        if log_callback:
            log_callback(msg)

    # 1. Collecte des cd_nom
    log("Collecte des cd_nom depuis les couches...")
    cd_nom_list = collect_cdnom_from_config(layer_config)
    if not cd_nom_list:
        return False, "Aucun cd_nom trouvé dans les couches sélectionnées."

    # locationId pour le département : INSEED + code_insee
    location_id = f"INSEED{code_insee_dept}"
    log(f"Requêtage API Statuts (locationId={location_id}, {len(cd_nom_list)} taxons)...")

    session = requests.Session()
    session.headers.update({"accept": "application/hal+json;version=1"})

    all_rows = []
    total_batches = (len(cd_nom_list) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(cd_nom_list), BATCH_SIZE):
        batch = cd_nom_list[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        if progress_callback:
            progress_callback(batch_num, total_batches, f"Lot {batch_num}/{total_batches}")
        status_list = fetch_status_batch(location_id, batch, session)
        for s in status_list:
            taxon = s.get("taxon") or {}
            all_rows.append({
                "cdnom": str(taxon.get("id", "")),
                "scientificName": (taxon.get("scientificName") or ""),
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

    # 2. Création couche mémoire (sans géométrie)
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
    temp_layer = QgsVectorLayer("None", "status_data_temp", "memory")
    temp_layer.dataProvider().addAttributes(fields)
    temp_layer.updateFields()

    for row in all_rows:
        feat = QgsFeature(temp_layer.fields())
        feat.setAttributes([
            row["cdnom"],
            row["scientificName"],
            row["statusTypeName"],
            row["statusTypeGroup"],
            row["statusCode"],
            row["statusName"],
            row["locationId"],
            row["locationName"],
            row["statusRemarks"],
            row["source"],
        ])
        temp_layer.dataProvider().addFeature(feat)

    # 3. Sauvegarde dans le GeoPackage (comme NaturaPivotHabitats / TaxrefApiToTable)
    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = "GPKG"
    save_options.layerName = "status_data"
    save_options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer
        if os.path.exists(gpkg_path)
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    err, err_msg = QgsVectorFileWriter.writeAsVectorFormatV3(
        temp_layer,
        gpkg_path,
        QgsProject.instance().transformContext(),
        save_options
    )
    if err != QgsVectorFileWriter.NoError:
        return False, f"Erreur sauvegarde GPKG : {err_msg}"
    log(f"Table status_data enregistrée : {len(all_rows)} lignes.")
    return True, f"{len(all_rows)} statuts enregistrés dans status_data."
