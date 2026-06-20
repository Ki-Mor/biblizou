# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : TaxrefApiToTable.py
Groupe : TaxRef
Description : Requêtage API TAXREF (taxa) et enregistrement dans biblizou.gpkg|data_taxref.
              Table sans géométrie. Anciennement TaxrefConsolidator.
"""
import requests
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsMessageLog,
    Qgis
)
from qgis.PyQt.QtCore import QVariant, pyqtSignal, QObject

from .base.ApiUtils import collect_cdnom_from_config, create_taxref_session
from .base.LayerUtils import LayerUtils


class TaxrefApiToTable(QObject):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self, gpkg_path):
        super().__init__()
        self.gpkg_path = gpkg_path
        self.session = create_taxref_session()

    def run(self, layer_config):
        """
        Args:
            layer_config: list of dicts [{'layer_id': '...', 'column': '...'}]
        Returns:
            (success: bool, message: str)
        """
        self.status_changed.emit("Collecte des codes uniques...")
        unique_codes = collect_cdnom_from_config(layer_config)

        if not unique_codes:
            return False, "Aucun code trouvé dans les couches sélectionnées."

        total = len(unique_codes)
        results = []
        all_keys = set()

        self.status_changed.emit(f"Requêtage API TAXREF ({total} taxons)...")
        for i, cd_nom in enumerate(unique_codes):
            try:
                response = self.session.get(
                    f"https://taxref.mnhn.fr/api/taxa/{cd_nom}", timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    flat_data = {k: str(v) for k, v in data.items() if not k.startswith('_')}
                    results.append(flat_data)
                    all_keys.update(flat_data.keys())

                self.progress_changed.emit(int((i / total) * 100))

            except Exception as e:
                QgsMessageLog.logMessage(
                    f"[TaxrefApiToTable]: Erreur API pour {cd_nom}: {e}",
                    "Biblizou", Qgis.Warning
                )

        if not results:
            return False, "Aucune donnée récupérée depuis l'API."

        sorted_keys = sorted(all_keys)
        if 'cdNom' in sorted_keys:
            sorted_keys.insert(0, sorted_keys.pop(sorted_keys.index('cdNom')))

        fields = [QgsField(key, QVariant.String) for key in sorted_keys]

        temp_layer = QgsVectorLayer("None?crs=EPSG:4326", "data_taxref", "memory")
        temp_layer.dataProvider().addAttributes(fields)
        temp_layer.updateFields()

        features = []
        for res in results:
            feat = QgsFeature(temp_layer.fields())
            feat.setAttributes([res.get(key, "") for key in sorted_keys])
            features.append(feat)

        temp_layer.dataProvider().addFeatures(features)

        success, err_msg = LayerUtils.save_to_gpkg(temp_layer, self.gpkg_path)
        if success:
            self.status_changed.emit("Table data_taxref enregistrée avec succès.")
            return True, f"{len(results)} taxons consolidés dans le GeoPackage."
        else:
            return False, f"Erreur de sauvegarde : {err_msg}"
