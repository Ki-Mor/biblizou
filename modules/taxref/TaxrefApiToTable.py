# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : TaxrefApiToTable.py
Groupe : TaxRef
Description : Requêtage API TAXREF (taxa) et enregistrement dans biblizou.gpkg|data_taxref.
              Table sans géométrie. Anciennement TaxrefConsolidator.
"""
from qgis.PyQt.QtCore import QVariant, pyqtSignal, QObject
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsMessageLog,
    Qgis
)

from ..base.ApiUtils import collect_cdnom_from_config, create_taxref_session
from ..base.LayerUtils import LayerUtils

API_TAXA = "https://taxref.mnhn.fr/api/taxa"
BATCH_SIZE = 50  # hypothèse médiane, taille max à mesurer (ticket dédié)

class TaxrefApiToTable(QObject):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self, gpkg_path):
        super().__init__()
        self.gpkg_path = gpkg_path
        self.session = create_taxref_session()

    def _fetch_batch(self, batch):
        """Requête un paquet de cd_nom. Renvoie la liste des taxons
        (dicts), ou None si la requête a échoué."""
        try:
            response = self.session.get(
                API_TAXA,
                params={"taxrefIds": ",".join(batch), "size": len(batch)},
                timeout=30)
            if response.status_code != 200:
                return None
            embedded = response.json().get("_embedded", {})
            for value in embedded.values():
                if isinstance(value, list):
                    return value
            return []
        except Exception as e:
            QgsMessageLog.logMessage(
                f"[TaxrefApiToTable]: Erreur API paquet de {len(batch)} : {e}",
                "Biblizou", Qgis.Warning)
            return None

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

        codes = sorted(str(c) for c in unique_codes)
        batches = [codes[i:i + BATCH_SIZE]
                   for i in range(0, len(codes), BATCH_SIZE)]

        self.status_changed.emit(
            f"Requêtage API TAXREF ({total} taxons, {len(batches)} paquets)...")
        for n, batch in enumerate(batches):
            taxa = self._fetch_batch(batch)
            if taxa:
                for data in taxa:
                    flat_data = {k: str(v) for k, v in data.items()
                                 if not k.startswith('_')}
                    results.append(flat_data)
                    all_keys.update(flat_data.keys())
            self.progress_changed.emit(int(((n + 1) / len(batches)) * 100))

        got = {r.get("id") for r in results}
        missing = [c for c in codes if c not in got]

        if not results:
            return False, "Aucune donnée récupérée depuis l'API."

        sorted_keys = sorted(all_keys)
        if 'cdNom' in sorted_keys:
            sorted_keys.insert(0, sorted_keys.pop(sorted_keys.index('cdNom')))

        fields = [QgsField(key, QVariant.String) for key in sorted_keys]

        temp_layer = QgsVectorLayer("None?crs=EPSG:4326", "data_taxref",
                                    "memory")
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
            self.status_changed.emit(
                "Table data_taxref enregistrée avec succès.")
            msg = f"{len(results)} taxons consolidés dans le GeoPackage."
            if missing:
                msg += (f" {len(missing)} cd_nom non résolus : "
                        f"{', '.join(missing[:20])}")
            return True, msg        else:
            return False, f"Erreur de sauvegarde : {err_msg}"
