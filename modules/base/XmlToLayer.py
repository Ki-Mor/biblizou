# -*- coding: utf-8 -*-
"""
Auteur : ExEco Environnement - François Botcazou
Nom : XmlToLayer.py
Groupe : base
Description : Classe abstraite (ABC) mutualisée pour l'extraction de données
              à partir de fichiers XML (ZNIEFF, Natura 2000) vers un GeoPackage.
"""

import os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsMessageLog,
    QgsVectorFileWriter,
    Qgis
)
from PyQt5.QtWidgets import QInputDialog, QMessageBox


class XmlToLayer(ABC):
    """
    Classe abstraite pour l'extraction XML vers couche QGIS / GeoPackage.

    Méthodes concrètes (mutualisées) :
        run_with_path(), process_folder(),
        save_to_geopackage(), load_from_geopackage(),
        log_message(), select_folder_dialog()

    Méthodes abstraites (à implémenter dans chaque classe enfant) :
        get_layer_name()   → nom de la couche QGIS et du layer dans le GPKG
        get_xml_filter()   → fonction de filtrage des fichiers XML du dossier
        process_xml_file() → parsing XML et extraction des données
        create_temp_layer()→ création de la couche mémoire QGIS avec les bons champs
    """

    def __init__(self):
        """Initialisation des attributs communs à tous les modules."""
        self.processed_files = 0
        self.total_records = 0
        self.gpkg_path = None
        self.gpkg_saved = False

    # -----------------------------------------------------------------------

    @abstractmethod
    def get_layer_name(self) -> str:
        """
        Retourne le nom de la couche QGIS et du layer dans le GeoPackage.
        Exemple : "Znieff_Habitats", "Natura_2000_Especes"
        """

    @abstractmethod
    def get_xml_filter(self) -> callable:
        """
        Retourne une fonction (lambda ou def) qui filtre les noms de fichiers XML.
        La fonction reçoit un nom de fichier (str) et retourne True/False.

        Exemples :
            ZNIEFF  → lambda f: f.endswith('.xml') and not f.startswith('FR') and len(f) == 13
            Natura  → lambda f: f.startswith('FR') and f.endswith('.xml') and len(f) == 13
        """

    @abstractmethod
    def process_xml_file(self, xml_path: str) -> list:
        """
        Parse un fichier XML individuel et retourne une liste de dictionnaires.
        Chaque dictionnaire représente un enregistrement (habitat, espèce, description...).

        Args:
            xml_path (str): chemin absolu vers le fichier XML
        Returns:
            list: liste de dicts, vide si aucune donnée trouvée
        """

    @abstractmethod
    def create_temp_layer(self, data: list):
        """
        Crée une couche mémoire QGIS sans géométrie à partir des données extraites.
        Définit les champs spécifiques au type de données (habitats, espèces, etc.)

        Args:
            data (list): liste de dicts retournée par process_xml_file()
        Returns:
            QgsVectorLayer: couche mémoire prête à être sauvegardée
        """

    # -----------------------------------------------------------------------

    def run_with_path(self, folder_path: str):
        """
        Point d'entrée en mode BiblizouMain (sans boîte de dialogue).

        Args:
            folder_path (str): chemin du dossier contenant les fichiers XML
        Returns:
            True  → données trouvées, couche créée et chargée
            None  → aucune donnée (situation normale, pas d'erreur)
            False → erreur technique
        """
        if not folder_path:
            self.log_message("Aucun dossier spécifié", Qgis.Warning)
            return False

        if not os.path.isdir(folder_path):
            self.log_message(f"Dossier introuvable : {folder_path}", Qgis.Warning)
            return False

        try:
            data = self.process_folder(folder_path)

            if not data:
                # Pas de données = situation normale (aire d'étude sans ce type de zonage)
                return None

            temp_layer = self.create_temp_layer(data)

            self.gpkg_path = os.path.join(folder_path, "biblizou.gpkg")
            self.save_to_geopackage(temp_layer)

            if self.gpkg_saved:
                self.load_from_geopackage()
            else:
                QgsProject.instance().addMapLayer(temp_layer)
                self.log_message("Couche temporaire ajoutée (échec sauvegarde GeoPackage)", Qgis.Warning)

            self.log_message(
                f"Traitement terminé — {self.processed_files} fichiers, {len(data)} enregistrements",
                Qgis.Success
            )
            return True

        except Exception as e:
            self.log_message(f"Erreur lors du traitement : {str(e)}", Qgis.Critical)
            return False

    def process_folder(self, folder_path: str) -> list:
        """
        Liste les fichiers XML du dossier selon le filtre de la classe enfant,
        puis appelle process_xml_file() sur chacun.

        Returns:
            list: tous les enregistrements extraits, tous fichiers confondus
        """
        all_data = []
        xml_filter = self.get_xml_filter()

        xml_files = [f for f in os.listdir(folder_path) if xml_filter(f)]

        if not xml_files:
            self.log_message(f"Aucun fichier XML trouvé dans {folder_path}", Qgis.Warning)
            return []

        self.log_message(f"{len(xml_files)} fichiers XML à traiter", Qgis.Info)

        for i, xml_file in enumerate(xml_files, 1):
            full_path = os.path.join(folder_path, xml_file)
            file_data = self.process_xml_file(full_path)

            if file_data:
                all_data.extend(file_data)
                self.processed_files += 1

            if i % 10 == 0 or i == len(xml_files):
                self.log_message(
                    f"Progression : {i}/{len(xml_files)} fichiers traités",
                    Qgis.Info
                )

        self.total_records = len(all_data)
        return all_data

    def save_to_geopackage(self, layer):
        """Enregistre la couche dans le GeoPackage (création ou remplacement du layer)."""
        try:
            gpkg_exists = os.path.exists(self.gpkg_path)

            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.driverName = "GPKG"
            save_options.layerName = self.get_layer_name()
            save_options.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer if gpkg_exists
                else QgsVectorFileWriter.CreateOrOverwriteFile
            )

            action = "existant" if gpkg_exists else "nouveau"
            self.log_message(f"GeoPackage {action} : {self.gpkg_path}", Qgis.Info)

            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                self.gpkg_path,
                QgsProject.instance().transformContext(),
                save_options
            )

            if error[0] == QgsVectorFileWriter.NoError:
                self.gpkg_saved = True
                self.log_message("Couche sauvegardée avec succès", Qgis.Success)
            else:
                self.gpkg_saved = False
                self.log_message(f"Erreur de sauvegarde : {error[1]}", Qgis.Critical)

        except Exception as e:
            self.gpkg_saved = False
            self.log_message(f"Exception lors de la sauvegarde : {str(e)}", Qgis.Critical)

    def load_from_geopackage(self):
        """Charge la couche depuis le GeoPackage et l'ajoute au projet QGIS."""
        try:
            layer_name = self.get_layer_name()
            uri = f"{self.gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, layer_name, "ogr")

            if layer.isValid():
                # Supprimer l'ancienne version si elle existe déjà dans le projet
                for old in QgsProject.instance().mapLayersByName(layer_name):
                    QgsProject.instance().removeMapLayer(old.id())

                QgsProject.instance().addMapLayer(layer)
                self.log_message("Couche chargée depuis le GeoPackage", Qgis.Success)
            else:
                self.log_message("Erreur : la couche chargée n'est pas valide", Qgis.Critical)

        except Exception as e:
            self.log_message(f"Erreur lors du chargement : {str(e)}", Qgis.Critical)

    def select_folder_dialog(self):
        """Ouvre une boîte de dialogue pour saisir le chemin du dossier (mode indépendant)."""
        folder_path, ok = QInputDialog.getText(
            None,
            "Sélection du dossier",
            f"Chemin du dossier contenant les fichiers XML ({self.get_layer_name()}) :"
        )

        if not ok or not folder_path:
            self.log_message("Annulation par l'utilisateur", Qgis.Info)
            return None

        if not os.path.isdir(folder_path):
            QMessageBox.warning(None, "Erreur", f"Le dossier '{folder_path}' n'existe pas.")
            return None

        return folder_path

    def log_message(self, message: str, level=Qgis.Info):
        """
        Enregistre un message dans le journal QGIS avec le nom de la classe comme préfixe.
        Le préfixe s'adapte automatiquement à la classe enfant (pas besoin de le redéfinir).
        """
        QgsMessageLog.logMessage(
            f"[{self.__class__.__name__}]: {message}",
            "Biblizou",
            level=level
        )