import os
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod

from qgis.core import (
    QgsProject,
    QgsMessageLog,
    Qgis
)
from PyQt5.QtWidgets import QInputDialog, QMessageBox

from .LayerUtils import LayerUtils


class XmlToLayer(ABC):
    """
    Classe abstraite pour l'extraction XML vers couche QGIS / GeoPackage.

    Méthodes concrètes (mutualisées) :
        run_with_path(), process_folder(),
        save_to_geopackage(), load_from_geopackage(),
        log_message(), select_folder_dialog()

    Méthodes abstraites (à implémenter dans chaque classe enfant) :
        get_layer_name()    → nom de la couche QGIS et du layer dans le GPKG
        get_xml_filter()    → fonction de filtrage des fichiers XML du dossier
        process_xml_file()  → parsing XML et extraction des données
        create_temp_layer() → création de la couche mémoire QGIS avec les bons champs
    """

    def __init__(self):
        self.processed_files = 0
        self.total_records = 0
        self.gpkg_path = None
        self.gpkg_saved = False

    # -----------------------------------------------------------------------

    @abstractmethod
    def get_layer_name(self) -> str:
        """Retourne le nom de la couche QGIS et du layer dans le GeoPackage."""

    @abstractmethod
    def get_xml_filter(self) -> callable:
        """Retourne une fonction lambda filtrant les noms de fichiers XML."""

    @abstractmethod
    def process_xml_file(self, xml_path: str) -> list:
        """Parse un fichier XML et retourne une liste de dicts."""

    @abstractmethod
    def create_temp_layer(self, data: list):
        """Crée une couche mémoire QGIS sans géométrie à partir des données extraites."""

    # -----------------------------------------------------------------------

    def run_with_path(self, folder_path: str):
        """
        Point d'entrée en mode BiblizouMain (sans boîte de dialogue).

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
                return None

            temp_layer = self.create_temp_layer(data)
            temp_layer.setName(self.get_layer_name())

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
        """Liste les fichiers XML et appelle process_xml_file() sur chacun."""
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
                self.log_message(f"Progression : {i}/{len(xml_files)} fichiers traités", Qgis.Info)

        self.total_records = len(all_data)
        return all_data

    def save_to_geopackage(self, layer):
        """Délègue la sauvegarde à LayerUtils et met à jour gpkg_saved."""
        action = "existant" if os.path.exists(self.gpkg_path) else "nouveau"
        self.log_message(f"GeoPackage {action} : {self.gpkg_path}", Qgis.Info)

        success, err_msg = LayerUtils.save_to_gpkg(layer, self.gpkg_path)
        self.gpkg_saved = success

        if success:
            self.log_message("Couche sauvegardée avec succès", Qgis.Success)
        else:
            self.log_message(f"Erreur de sauvegarde : {err_msg}", Qgis.Critical)

    def load_from_geopackage(self):
        """Délègue le chargement à LayerUtils et la substitution de couche."""
        layer = LayerUtils.load_from_gpkg(self.gpkg_path, self.get_layer_name())

        if layer:
            LayerUtils.replace_layer(layer)
            self.log_message("Couche chargée depuis le GeoPackage", Qgis.Success)
        else:
            self.log_message("Erreur : la couche chargée n'est pas valide", Qgis.Critical)

    def select_folder_dialog(self):
        """Ouvre une boîte de dialogue pour saisir le chemin du dossier."""
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
        """Enregistre un message dans le journal QGIS."""
        QgsMessageLog.logMessage(
            f"[{self.__class__.__name__}]: {message}",
            "Biblizou",
            level=level
        )