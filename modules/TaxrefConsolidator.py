# -*- coding: utf-8 -*-
import os
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
from qgis.PyQt.QtCore import QVariant, pyqtSignal, QObject

class TaxrefConsolidator(QObject):
    # Signaux pour la barre de progression (utile pour ton futur DockWidget)
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)

    def __init__(self, gpkg_path):
        super().__init__()
        self.gpkg_path = gpkg_path
        self.session = requests.Session()
        self.session.headers.update({"accept": "application/hal+json;version=1"})

    def run(self, layer_config):
        """
        layer_config: list of dicts [{'layer_id': '...', 'column': '...'}]
        """
        unique_codes = set()
        
        # 1. Collecte des codes uniques
        self.status_changed.emit("Collecte des codes uniques...")
        for config in layer_config:
            layer = QgsProject.instance().mapLayer(config['layer_id'])
            if not layer: continue
            
            idx = layer.fields().lookupField(config['column'])
            for feat in layer.getFeatures():
                val = feat.attributes()[idx]
                if val is not None and str(val).strip():
                    # Gestion du cas 123.0 (Excel) : on prend ce qu'il y a avant le point
                    str_val = str(val).split('.')[0]
                    # Nettoyage : on ne garde que les chiffres si c'est du texte
                    clean_val = "".join(filter(str.isdigit, str(val)))
                    if clean_val:
                        unique_codes.add(clean_val)

        if not unique_codes:
            return False, "Aucun code trouvé dans les couches sélectionnées."

        # 2. Requêtage API TAXREF
        total = len(unique_codes)
        results = []
        all_keys = set()
        
        self.status_changed.emit(f"Requêtage API TAXREF ({total} taxons)...")
        for i, cd_nom in enumerate(unique_codes):
            try:
                url = f"https://taxref.mnhn.fr/api/taxa/{cd_nom}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    # On nettoie les données (on enlève les liens _links complexes)
                    flat_data = {k: str(v) for k, v in data.items() if not k.startswith('_')}
                    results.append(flat_data)
                    all_keys.update(flat_data.keys())
                
                self.progress_changed.emit(int((i / total) * 100))
            except Exception as e:
                QgsMessageLog.logMessage(f"Erreur API pour {cd_nom}: {e}", "Biblizou", Qgis.Warning)

        if not results:
            return False, "Aucune donnée récupérée depuis l'API."

        # 3. Création de la couche de sortie (Table sans géométrie)
        fields = []
        # On s'assure que CD_NOM est en premier
        sorted_keys = sorted(list(all_keys))
        if 'cdNom' in sorted_keys:
            sorted_keys.insert(0, sorted_keys.pop(sorted_keys.index('cdNom')))

        for key in sorted_keys:
            fields.append(QgsField(key, QVariant.String))

        temp_layer = QgsVectorLayer("None?crs=EPSG:4326", "data_taxref_temp", "memory")
        temp_layer.dataProvider().addAttributes(fields)
        temp_layer.updateFields()

        # Remplissage
        features = []
        for res in results:
            feat = QgsFeature(temp_layer.fields())
            attrs = [res.get(key, "") for key in sorted_keys]
            feat.setAttributes(attrs)
            features.append(feat)
        
        temp_layer.dataProvider().addFeatures(features)

        # 4. Sauvegarde dans le GeoPackage
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = "GPKG"
        save_options.layerName = "data_taxref"
        save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(self.gpkg_path) else QgsVectorFileWriter.CreateOrOverwriteFile

        error, msg = QgsVectorFileWriter.writeAsVectorFormatV3(
            temp_layer,
            self.gpkg_path,
            QgsProject.instance().transformContext(),
            save_options
        )

        if error == QgsVectorFileWriter.NoError:
            self.status_changed.emit("Table data_taxref enregistrée avec succès.")
            return True, f"{len(results)} taxons consolidés dans le GeoPackage."
        else:
            return False, f"Erreur de sauvegarde : {msg}"