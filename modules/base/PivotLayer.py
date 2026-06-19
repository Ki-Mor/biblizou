# -*- coding: utf-8 -*-
"""
Auteur : ExEco Environnement - François Botcazou
Date : 2026/06
Version : 1.0
Nom : XmlToLayer.py
Groupe : base
Description : Classe abstraite (ABC) pour la création de tableaux croisés dynamiques (pivots)
    à partir de couches QGIS. Les colonnes représentent les sites, les lignes les entités
    (habitats ou espèces).
"""

import unicodedata
from abc import ABC, abstractmethod

from qgis.core import QgsProject, QgsVectorLayer, QgsMessageLog, Qgis


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

    def __init__(self):
        self.source_layer = None

    # -----------------------------------------------------------------------
    # Méthodes abstraites
    # -----------------------------------------------------------------------

    @abstractmethod
    def get_source_layer_name(self) -> str:
        """Retourne le nom de la couche source dans le projet QGIS."""

    @abstractmethod
    def get_output_layer_name(self) -> str:
        """Retourne le nom de la couche pivot à créer."""

    @abstractmethod
    def get_site_keys(self) -> tuple:
        """
        Retourne un tuple (code_field, name_field) identifiant les champs
        utilisés pour construire les colonnes du pivot.
        Exemple : ('NM_SFFZN', 'LB_ZN') ou ('SITECODE', 'SITE_NAME')
        """

    @abstractmethod
    def build_pivot_query(self) -> str:
        """
        Construit et retourne la requête SQL complète du pivot.
        Doit utiliser self.source_layer et self.get_sites() pour les colonnes.
        Retourne None en cas d'erreur.
        """

    # -----------------------------------------------------------------------
    # Méthodes concrètes
    # -----------------------------------------------------------------------

    def run(self) -> bool:
        """Point d'entrée principal."""
        if not self.load_source_layer():
            return False

        sql_query = self.build_pivot_query()
        if not sql_query:
            return False

        return self.create_virtual_layer(sql_query)

    def load_source_layer(self) -> bool:
        """Charge la couche source depuis le projet QGIS."""
        layer_name = self.get_source_layer_name()
        layers = QgsProject.instance().mapLayersByName(layer_name)

        if not layers:
            self.log(f"Couche '{layer_name}' introuvable dans le projet", Qgis.Critical)
            return False

        self.source_layer = layers[0]

        if not self.source_layer.isValid():
            self.log(f"Couche '{layer_name}' invalide", Qgis.Critical)
            return False

        if self.source_layer.featureCount() == 0:
            self.log(f"Couche '{layer_name}' vide", Qgis.Warning)
            return False

        self.log(f"Couche source '{layer_name}' chargée", Qgis.Info)
        return True

    def get_sites(self) -> dict:
        """
        Extrait les couples (code, nom) uniques depuis la couche source.
        Utilise les champs définis par get_site_keys().
        Retourne un dict {code: nom}.
        """
        code_field, name_field = self.get_site_keys()
        sites = {}

        try:
            for feat in self.source_layer.getFeatures():
                code = feat[code_field]
                name = feat[name_field]
                if code:
                    sites[code] = name if name else "Sans nom"
        except KeyError as e:
            self.log(f"Champ manquant : {e}", Qgis.Critical)

        if not sites:
            self.log("Aucun site trouvé dans la couche", Qgis.Warning)

        return sites

    def create_virtual_layer(self, sql_query: str) -> bool:
        """Crée la couche virtuelle pivot et l'ajoute au projet QGIS."""
        output_name = self.get_output_layer_name()

        virtual_layer = QgsVectorLayer(f"?query={sql_query}", output_name, "virtual")

        if not virtual_layer.isValid():
            self.log(f"Couche virtuelle '{output_name}' invalide — vérifiez la requête SQL", Qgis.Critical)
            return False

        # Supprimer l'ancienne version si elle existe
        for old in QgsProject.instance().mapLayersByName(output_name):
            QgsProject.instance().removeMapLayer(old.id())

        QgsProject.instance().addMapLayer(virtual_layer)
        self.log(
            f"Pivot '{output_name}' créé ({virtual_layer.featureCount()} enregistrements)",
            Qgis.Success
        )
        return True

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
