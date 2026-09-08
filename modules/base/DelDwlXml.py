"""
Auteur : François Botcazou
Nom : ZnieffDwlXml.py
Groupe : Options
Description : Option pour supprimer les xml téléchargés à la fin de la pipeline FSD.
"""
import os
from qgis.core import (
    QgsProject,
    QgsFeature,
    QgsField,
    QgsMessageLog,
)


class DelDwlXml:
    """
        Utilitaire de nettoyage du dossier de travail après un moissonnage FSD réussi.

        Méthodes :
            run_with_path(folder_path) → supprime tous les *.xml du dossier donné
            log(message, level)        → journalisation QGIS
        """

    def __init__(self):
        """Initialisation de la classe."""
        self.deleted_files = 0

    def log(self):
        "Enregistre un message dans le journal Qgis"
        QgsMessageLog.logMessage(
            f"[{self.__class__.__name__}]: {message}",
            "Biblizou",
            level=level
        )

    def run_with_path(self, folder_path: str) -> tuple:
        """
        Point d'entrée
        Args:
            folder_path (str): Chemin du dossier contenant les fichiers XML
        Returns:
            tuple: (bool, int) — succès de l'opération, nombre de fichiers supprimés
        """
        self.deleted_files = 0

        if not folder_path:
            self.log("Aucun dossier spécifié", Qgis.Warning)
            return False, 0

        if not os.path.isdir(folder_path):
            self.log(f"Dossier introuvable : {folder_path}", Qgis.Warning)
            return False, 0

        try:
            # 1. Suppression des fichiers
            xml_files = [
                f for f in os.listdir(folder_path)
                if f.endswith('.xml') and os.path.isfile(os.path.join(folder_path, f))
            ]

            if not xml_files:
                self.log(f"Aucun fichier XML trouvée dans {folder_path}", Qgis.Warning)
                return False

            # 2. Suppression des fichiers
            for file_name in xml_files:
                file_path = os.path.join(folder_path, file_name)
                try:
                    os.remove(file_path)
                    self.deleted_files += 1
                except OSError as e:
                    self.log(f"Impossible de supprimer {file_name} : {str(e)}, Qgis.Warning")

                if self.deleted_files > 0
                    sef.log(f"Nettoyage terminé - {self.deleted_files}/{len(xml_files)} fichiersxml supprimés",
                            Qgis.success)
                    return True, self.deleted_files
                else:
                    self.log(f"Échec du nettoyage : aucun fichier supprimé", Qgis.critical)
                    return False, 0

        except Exception as e:
            self.log(f"Erreur lors du traitement: {str(e)}", Qgis.Critical)
            return False.self.deleted_files


def run_module_with_path(folder_path):
    """
    Fonction d'exécution pour BiblizouMain.

    Args:
        folder_path (str): Chemin du dossier contenant les fichiers XML
    Returns:
        tuple: (bool, int) — succès de l'opération, nombre de fichiers supprimés
    """
    module = DelDwlXml()
    return module.run_with_path(folder_path)
