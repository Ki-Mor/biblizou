# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : StatusPivotByGroup.py
Groupe : Status
Description : Crée une table pivot par statusTypeGroup : en lignes cdnom, nom latin,
              nom vernaculaire ; en colonnes statusTypeName ; en valeur statusCode.
              Utilise la table status_data_joined (ou status_data) du GeoPackage.
"""

import re
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsMessageLog,
    Qgis
)


def _sanitize_layer_name(name):
    """Retourne un nom de couche sans caractères problématiques."""
    return re.sub(r"[^\w]", "_", str(name)).strip("_") or "Statuts"


def _get_vernacular_field(fields):
    """Retourne le nom du champ vernaculaire (nom_vern via API, ou colonnes TaxRef)."""
    for cand in ("nom_vern", "vernacularName1", "nomVern", "taxref_vernacularName1", "taxref_nomVern"):
        if fields.indexOf(cand) != -1:
            return cand
    return "scientificName"


def run(gpkg_path, progress_callback=None, log_callback=None):
    """
    Charge status_data_joined (ou status_data) depuis le GeoPackage, crée une
    couche virtuelle pivot par statusTypeGroup et l'ajoute au projet.
    
    Returns:
        (success: bool, message: str)
    """
    def log(msg):
        QgsMessageLog.logMessage(msg, "Biblizou", level=Qgis.Info)
        if log_callback:
            log_callback(msg)

    uri_joined = f"{gpkg_path}|layername=status_data_joined"
    uri_status = f"{gpkg_path}|layername=status_data"

    layer = QgsVectorLayer(uri_joined, "status_data_joined", "ogr")
    if not layer.isValid():
        layer = QgsVectorLayer(uri_status, "status_data", "ogr")
    if not layer.isValid():
        return False, "Aucune table status_data ou status_data_joined dans le GeoPackage."

    # Ajouter au projet pour que la couche virtuelle puisse référencer la table par id
    existing = QgsProject.instance().mapLayersByName(layer.name())
    for ex in existing:
        QgsProject.instance().removeMapLayer(ex.id())
    QgsProject.instance().addMapLayer(layer)
    layer_id = layer.id()

    vern_fld = _get_vernacular_field(layer.fields())
    # Charger la couche en mémoire pour lire les groupes/types
    groups_types = {}  # statusTypeGroup -> [statusTypeName, ...]
    for feat in layer.getFeatures():
        g = feat["statusTypeGroup"] or ""
        t = feat["statusTypeName"] or ""
        if not g:
            continue
        if g not in groups_types:
            groups_types[g] = set()
        groups_types[g].add(t)

    if not groups_types:
        return False, "Aucun statusTypeGroup trouvé dans la table."

    created = 0
    for group_name, type_names in groups_types.items():
        sorted_types = sorted(type_names)
        case_parts = []
        for st in sorted_types:
            safe_alias = st.replace('"', '""')
            st_esc = st.replace("'", "''")
            case_parts.append(
                f"MAX(CASE WHEN statusTypeName = '{st_esc}' THEN statusCode END) AS \"{safe_alias}\""
            )
        cols = ", ".join(case_parts)
        safe_vern = vern_fld.replace('"', '""')
        group_esc = group_name.replace("'", "''")
        query = (
            f'SELECT cdnom, scientificName AS nom_latin, "{safe_vern}" AS nom_vernaculaire, {cols} '
            f'FROM "{layer_id}" '
            f"WHERE statusTypeGroup = '{group_esc}' "
            f'GROUP BY cdnom, scientificName, "{safe_vern}" '
            f'ORDER BY scientificName'
        )
        vlayer = QgsVectorLayer(f"?query={query}", f"Statuts_Pivot_{_sanitize_layer_name(group_name)}", "virtual")
        if vlayer.isValid():
            existing = QgsProject.instance().mapLayersByName(vlayer.name())
            for ex in existing:
                QgsProject.instance().removeMapLayer(ex.id())
            QgsProject.instance().addMapLayer(vlayer)
            created += 1
            log(f"Pivot créé : {vlayer.name()}")
        else:
            QgsMessageLog.logMessage(
                f"StatutsPivot: Erreur création pivot pour groupe '{group_name}'",
                "Biblizou",
                level=Qgis.Warning
            )

    if created == 0:
        return False, "Aucune couche pivot n'a pu être créée."
    return True, f"{created} table(s) pivot créée(s) par groupe de statuts."
