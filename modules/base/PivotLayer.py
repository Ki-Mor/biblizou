# -*- coding: utf-8 -*-
"""
Auteur : ExEco Environnement - François Botcazou
Nom : PivotLayer.py
Groupe : base
Description : Classe abstraite (ABC) pour la création de tableaux croisés dynamiques (pivots)
              à partir de couches QGIS. Les colonnes représentent les sites, les lignes les entités
              (habitats ou espèces).
"""
import os
import unicodedata
from abc import ABC, abstractmethod

from qgis.core import QgsVectorLayer, QgsMessageLog, QgsProject, Qgis
from .LayerUtils import LayerUtils


class PivotLayer(ABC):
    """
    Classe abstraite mutualisée pour la création de tableaux croisés dynamiques (pivots)
    à partir de couches QGIS. Les colonnes représentent les sites, les lignes les entités
    (habitats ou espèces).

    Méthodes concrètes (mutualisées) :
        run(), load_source_layer(), create_virtual_layer(), remove_accents()

    Méthodes abstraites (à implémenter dans chaque classe enfant) :
        get_source_layer_name() → nom de la couche source dans le projet QGIS
        get_output_layer_name() → nom de la couche pivot à créer
        get_site_keys()         → tuple (code_field, name_field) pour extraire les sites
        build_pivot_query()     → requête SQL complète du pivot
    """

    # -----------------------------------------------------------------------

    def __init__(self):
        self.source_layer = None

    @abstractmethod
    def get_source_layer_name(self) -> str:
        pass

    @abstractmethod
    def get_output_layer_name(self) -> str:
        pass

    @abstractmethod
    def get_site_keys(self) -> tuple:
        pass

    @abstractmethod
    def build_pivot_query(self) -> str:
        pass

    # -----------------------------------------------------------------------

    def load_source_layer(self) -> bool:
        """Charge et valide la couche source depuis le projet QGIS via le LayerUtils."""
        source_name = self.get_source_layer_name()
        self.source_layer = LayerUtils.get_layer(source_name)

        if not self.source_layer:
            self.log(f"Couche source '{source_name}' introuvable dans le projet", Qgis.Warning)
            return False

        if not self.source_layer.isValid():
            self.log(f"Couche source '{source_name}' présente mais non valide", Qgis.Critical)
            return False

        return True

    def get_sites(self) -> dict:
        """
        Extrait la liste unique des sites (paires code: nom) depuis la couche source.
        Pattern Template Method : utilise get_site_keys() défini par l'enfant.
        """
        if not self.source_layer and not self.load_source_layer():
            return {}

        code_field, name_field = self.get_site_keys()
        sites = {}

        for feature in self.source_layer.getFeatures():
            code = feature[code_field]
            name = feature[name_field]
            if code and str(code).strip():
                sites[str(code).strip()] = str(name).strip() if name else f"Site {code}"

        return sites

    def run(self, gpkg_path: str = None) -> bool:
        """Exécute la chaîne complète de génération du pivot."""
        self.log(f"Démarrage du pivot pour {self.__class__.__name__}", Qgis.Info)

        if not self.load_source_layer():
            return False

        sql_query = self.build_pivot_query()
        if not sql_query:
            self.log("Aucune donnée ou site trouvé pour construire le pivot SQL", Qgis.Warning)
            return False

        layer = self.create_virtual_layer(sql_query)
        if not layer:
            return False

        self.export_to_geopackage(layer, gpkg_path)
        return True

    def create_virtual_layer(self, sql_query: str) -> QgsVectorLayer | None:
        """Génère la couche virtuelle SQL et l'injecte/substitue via le LayerUtils."""
        output_name = self.get_output_layer_name()
        virtual_layer = QgsVectorLayer(f"?query={sql_query}", output_name, "virtual")

        if not virtual_layer.isValid():
            self.log(f"Couche virtuelle '{output_name}' invalide — vérifiez la requête SQL", Qgis.Critical)
            return None

        if LayerUtils.replace_layer(virtual_layer):
            self.log(
                f"Pivot '{output_name}' créé ({virtual_layer.featureCount()} enregistrements)",
                Qgis.Success
            )
            return virtual_layer  # ← retourne la couche

        return None

    def export_to_geopackage(self, layer: QgsVectorLayer, gpkg_path: str = None):
        """Exporte de façon persistante la couche générée via le LayerUtils."""
        if not gpkg_path:
            project_dir = os.path.dirname(QgsProject.instance().fileName())
            if not project_dir:
                self.log("Projet non sauvegardé et aucun chemin gpkg fourni", Qgis.Warning)
                return
            gpkg_path = os.path.join(project_dir, "biblizou.gpkg")

        success, err_msg = LayerUtils.save_to_gpkg(layer, gpkg_path)

        if success:
            self.log(f"Couche pivot enregistrée dans '{layer.name()}' ({gpkg_path})", Qgis.Success)
        else:
            self.log(f"Échec de l'export GeoPackage : {err_msg}", Qgis.Critical)

    def remove_accents(self, text: str) -> str:
        """Supprime les diacritiques d'une chaîne (à â é è ë ê î ô ù...)."""
        if not text:
            return text
        nfd = unicodedata.normalize('NFD', str(text))
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

    def col_alias(self, code: str, name: str) -> str:
        """Génère l'alias de colonne au format '[code] - [NOM_SITE]'."""
        nom_site = self.remove_accents(str(name)).upper()
        return f"{code} - {nom_site}".replace('"', '""')

    def log(self, message: str, level=Qgis.Info):
        """Enregistre un message dans le journal QGIS."""
        QgsMessageLog.logMessage(
            f"[{self.__class__.__name__}]: {message}",
            "Biblizou",
            level=level
        )
