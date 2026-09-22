# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : StatusJoinPatri.py
Groupe : bdc
Description : Enrichit la table status_data avec une colonne patri selon l'état de l'ui biblizou_dialog_patri.
              À condition que la checkbox cBPatri de biblizou_dialog_patri soit checked.
"""

from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsField,
    QgsMessageLog,
    Qgis
)

from ..base.LayerUtils import LayerUtils

def _test_condition(status_type_name: str, status_code: str, conditions) -> bool:
    """Vérifie si la couche existe, et valide et contient des entités."""

    for condition in conditions:
        if condition["statusTypeName"] == status_type_name and (
                condition.get("statusCode") is None or condition.get("statusCode") == status_code):
            return True
    return False

def run(gpkg_path: str, conditions, layer_name: str = "status_data", log_callback=None) -> tuple[bool, str]:
    """
    Ajoute une colonne booléenne patri à layer_name (par défaut status_data), à True pour toute ligne dont le statut
    correspond à au moins une des conditions (test via _test_condition).
        Args:
            gpkg_path: chemin vers biblizou.gpkg
            conditions: état de biblizou_dialog_patri.py. liste de dicts [{'statusTypeName': '...', 'statusCode': '...' (optionnel)}]
            layer_name: layer status_data obtenue de StatusApiToTable
            log_callback: optional (message)
        Returns:
            (success: bool, message: str)
        """

    def log(msg):
        QgsMessageLog.logMessage(f"[StatusJoinPatri]: {msg}", "Biblizou", Qgis.Info)
        if log_callback:
            log_callback(msg)

    layer_status = LayerUtils.load_from_gpkg(gpkg_path, layer_name)
    if layer_status is None:
        return False, f"Avertissement : aucune couche {layer_name} trouvée dans le GeoPackage."

    def compute_fn(feat):
        status_type_name = feat["statusTypeName"]
        status_code = feat["statusCode"]
        is_patri = _test_condition(status_type_name, status_code, conditions)
        return [is_patri]

    new_fields = [QgsField("patri", QVariant.Bool)]

    layer_joined = LayerUtils.add_computed_fields(
        layer_status, new_fields, compute_fn, output_name=f"{layer_name}_joined"
    )
    if layer_joined is None:
        return False, "Avertissement : aucune correspondance patrimoniale calculée."

    success, err_msg = LayerUtils.save_to_gpkg(layer_joined, gpkg_path)
    if not success:
        return False, f"Erreur sauvegarde GPKG : {err_msg}"

    log("Colonne patri ajoutée à status_data.")
    return True, "Colonne patri ajoutée à status_data."


def _test_condition(status_type_name: str, status_code: str, conditions) -> bool:
    """Vérifie si la couche existe, et valide et contient des entités."""

    for condition in conditions:
        if condition["statusTypeName"] == status_type_name and (
                condition.get("statusCode") is None or condition.get("statusCode") == status_code):
            return True
    return False
