# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : StatusJoinTaxref.py
Groupe : Status
Description : Enrichit la table status_data avec nom vernaculaire et groupe taxonomique
              obtenus par requête API TaxRef (GET taxa/{cd_nom}), comme TaxrefApiToTable.
              Enregistre le résultat dans biblizou.gpkg|status_data_joined.
              Plus de jointure avec la table data_taxref.
"""
import os
import time
import requests
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsMessageLog,
    QgsVectorFileWriter,
    QgsProject,
    Qgis
)
from qgis.PyQt.QtCore import QVariant

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


def run(gpkg_path, progress_callback=None, log_callback=None):
    """
    Charge status_data depuis gpkg_path, pour chaque cdnom distinct appelle l'API TaxRef
    pour récupérer nom vernaculaire et groupe, puis crée status_data_joined
    (status_data + nom_vern + groupe). Pas de jointure avec la table data_taxref.

    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        QgsMessageLog.logMessage(msg, "Biblizou", level=Qgis.Info)
        if log_callback:
            log_callback(msg)

    uri_status = f"{gpkg_path}|layername=status_data"
    layer_status = QgsVectorLayer(uri_status, "status_data", "ogr")

    if not layer_status.isValid():
        return False, "Couche status_data introuvable ou invalide dans le GeoPackage."

    idx_cdnom = layer_status.fields().indexOf("cdnom")
    if idx_cdnom == -1:
        return False, "Champ cdnom absent de status_data."

    # Cdnom distincts
    cdnoms = set()
    for feat in layer_status.getFeatures():
        v = feat.attributes()[idx_cdnom]
        if v is not None:
            key = str(v).split(".")[0].strip()
            if key:
                cdnoms.add(key)

    if not cdnoms:
        return False, "Aucun cdnom dans status_data."

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

    # Nouvelle couche : champs status_data + nom_vern + groupe
    fs = layer_status.fields()
    out_fields = [QgsField(f.name(), QVariant.String) for f in fs]
    out_fields.append(QgsField("nom_vern", QVariant.String))
    out_fields.append(QgsField("groupe", QVariant.String))

    temp = QgsVectorLayer("None", "status_data_joined_temp", "memory")
    temp.dataProvider().addAttributes(out_fields)
    temp.updateFields()

    count = 0
    for feat in layer_status.getFeatures():
        cdnom = feat.attributes()[idx_cdnom]
        if cdnom is None:
            continue
        key = str(cdnom).split(".")[0].strip()
        if not key:
            continue
        info = taxon_info.get(key, {"nom_vern": "", "groupe": ""})
        new_feat = QgsFeature(temp.fields())
        new_feat.setAttributes(list(feat.attributes()) + [info["nom_vern"], info["groupe"]])
        temp.dataProvider().addFeature(new_feat)
        count += 1

    if count == 0:
        return False, "Aucune ligne à enregistrer dans status_data_joined."

    save_options = QgsVectorFileWriter.SaveVectorOptions()
    save_options.driverName = "GPKG"
    save_options.layerName = "status_data_joined"
    save_options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer
        if os.path.exists(gpkg_path)
        else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    err, err_msg = QgsVectorFileWriter.writeAsVectorFormatV3(
        temp,
        gpkg_path,
        QgsProject.instance().transformContext(),
        save_options
    )
    if err != QgsVectorFileWriter.NoError:
        return False, f"Erreur sauvegarde status_data_joined : {err_msg}"
    log(f"Table status_data_joined enregistrée : {count} lignes (nom_vern et groupe via API).")
    return True, f"Enrichissement terminé : {count} lignes dans status_data_joined (API TaxRef)."

