# -*- coding: utf-8 -*-
"""
Auteur : ExEco Environnement - François Botcazou
Date : 2026/06
Version : 1.0
Nom : LayerManager.py
Groupe : base
Description : Classe utilitaire centralisant la gestion, la validation, le chargement,
              la création de GeoPackage et la substitution des couches vectorielles au sein de QGIS.
"""

from qgis.core import QgsProject, QgsVectorLayer, QgsProviderRegistry
import os


class LayerManager:

    @staticmethod
    def get_layer(name: str) -> QgsVectorLayer | None:
        """Retourne la première instance de couche correspondant au nom exact, ou None."""
        layers = QgsProject.instance().mapLayersByName(name)
        return layers[0] if layers else None

    @staticmethod
    def layer_is_ready(name: str) -> bool:
        """Vérifie si la couche existe, est valide et contient des entités."""
        layer = LayerManager.get_layer(name)
        if layer is None or not layer.isValid():
            return False
        return layer.featureCount() > 0

    @staticmethod
    def replace_layer(layer: QgsVectorLayer) -> bool:
        """Supprime de manière atomique l'ancienne version d'une couche par son nom et ajoute la nouvelle."""
        if not layer or not layer.isValid():
            return False

        project = QgsProject.instance()
        old_layer = LayerManager.get_layer(layer.name())
        if old_layer:
            project.removeMapLayer(old_layer.id())

        project.addMapLayer(layer)
        return True

    @staticmethod
    def load_from_gpkg(gpkg_path: str, name: str) -> QgsVectorLayer | None:
        """Charge une couche vectorielle spécifique depuis un fichier GeoPackage."""
        if not os.path.exists(gpkg_path):
            return None

        source = f"{gpkg_path}|layername={name}"
        layer = QgsVectorLayer(source, name, "ogr")
        return layer if layer.isValid() else None

    @staticmethod
    def create_empty_gpkg(gpkg_path: str) -> bool:
        """Crée physiquement un fichier GeoPackage vide s'il n'existe pas déjà."""
        if os.path.exists(gpkg_path):
            return True

        options = {}
        err = QgsProviderRegistry.instance().createProvider("ogr", gpkg_path, options)
        return err is None