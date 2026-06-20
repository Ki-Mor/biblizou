"""
Auteur : ExEco Environnement - François Botcazou
Nom : DwlXml.py
Groupe : base
Description : Classe abstraite (ABC) mutualisée pour l'extraction de données
              à partir de l'API de l'INPN vers une table.
"""

import os
import requests
import time
from abc import ABC, abstractmethod

from qgis.core import (
    QgsProject,
    QgsFeatureRequest,
    QgsMessageLog,
    QgsCoordinateTransform,
    QgsGeometry,
    Qgis
)


class DwlXml(ABC):
    """
    Classe abstraite mutualisée pour le téléchargement des fichiers XML
    depuis l'INPN (Natura 2000, ZNIEFF) dans un périmètre donné.

    Méthodes concrètes (mutualisées) :
        run_with_path(), find_patrinat_layers(), selectionner_et_stocker(),
        download_file(), execute_download(), log()

    Méthodes abstraites (à implémenter dans chaque classe enfant) :
        get_patrinat_layer_names() → tuple (nom_couche_1, nom_couche_2)
        build_url(id)              → URL de téléchargement pour un identifiant
    """

    def __init__(self):
        self.patrinat_layer_1 = None
        self.patrinat_layer_2 = None
        self.ids_1 = []
        self.ids_2 = []
        self.ae_eloignee = None
        self.download_folder = None
        self.files_downloaded = 0

    # -----------------------------------------------------------------------

    @abstractmethod
    def get_patrinat_layer_names(self) -> tuple:
        """
        Retourne les noms des deux couches Patrinat à rechercher dans le projet.
        Exemple : ('Patrinat : SIC', 'Patrinat : ZPS')
                  ('Patrinat : ZNIEFF1', 'Patrinat : ZNIEFF2')
        """

    @abstractmethod
    def build_url(self, zone_id: str) -> str:
        """
        Construit l'URL de téléchargement pour un identifiant de zone.
        Exemple Natura : f"https://inpn.mnhn.fr/docs/natura2000/fsdxml/{zone_id}.xml"
        Exemple ZNIEFF  : f"https://inpn.mnhn.fr/docs/ZNIEFF/znieffxml/{zone_id}.xml"
        """

    # -----------------------------------------------------------------------

    def run_with_path(self, reference_layer, folder_path: str) -> bool:
        """
        Point d'entrée pour BiblizouMain (sans boîtes de dialogue).

        Args:
            reference_layer (QgsVectorLayer): Couche de référence (aire d'étude)
            folder_path (str): Chemin du dossier de téléchargement
        Returns:
            bool: True si au moins un fichier téléchargé, False sinon
        """
        try:
            if not self.find_patrinat_layers():
                self.log("Couches Patrinat introuvables", Qgis.Warning)
                return False

            if not reference_layer:
                self.log("Couche de référence non définie", Qgis.Warning)
                return False

            if not os.path.isdir(folder_path):
                self.log(f"Dossier introuvable : {folder_path}", Qgis.Warning)
                return False

            self.ae_eloignee = reference_layer
            self.download_folder = folder_path

            return self.execute_download()

        except Exception as e:
            self.log(f"Erreur lors du téléchargement : {str(e)}", Qgis.Critical)
            return False

    def find_patrinat_layers(self) -> bool:
        """Recherche les deux couches Patrinat dans le projet QGIS."""
        name_1, name_2 = self.get_patrinat_layer_names()

        try:
            layers_1 = QgsProject.instance().mapLayersByName(name_1)
            layers_2 = QgsProject.instance().mapLayersByName(name_2)

            if layers_1:
                self.patrinat_layer_1 = layers_1[0]
                self.log(f"Couche '{name_1}' trouvée", Qgis.Info)
            else:
                self.log(f"Couche '{name_1}' introuvable", Qgis.Warning)

            if layers_2:
                self.patrinat_layer_2 = layers_2[0]
                self.log(f"Couche '{name_2}' trouvée", Qgis.Info)
            else:
                self.log(f"Couche '{name_2}' introuvable", Qgis.Warning)

            return self.patrinat_layer_1 is not None and self.patrinat_layer_2 is not None

        except Exception as e:
            self.log(f"Erreur recherche couches Patrinat : {str(e)}", Qgis.Critical)
            return False

    def selectionner_et_stocker(self, couche_source, liste_stockage: list):
        """Sélectionne les entités intersectant ae_eloignee et stocke leurs id_mnhn."""
        if not couche_source or not self.ae_eloignee:
            self.log("Couche source ou aire d'étude introuvable", Qgis.Warning)
            return

        try:
            transform = QgsCoordinateTransform(
                self.ae_eloignee.crs(),
                couche_source.crs(),
                QgsProject.instance()
            )

            geometries = [f.geometry() for f in self.ae_eloignee.getFeatures()]

            if not geometries:
                self.log("Aucune géométrie trouvée dans l'aire d'étude", Qgis.Warning)
                return

            geom_ref = QgsGeometry.unaryUnion(geometries)
            geom_ref.transform(transform)

            couche_source.removeSelection()
            ids_selectionnes = []
            liste_stockage.clear()

            request = QgsFeatureRequest().setFilterRect(geom_ref.boundingBox())
            for feature in couche_source.getFeatures(request):
                if feature.geometry().intersects(geom_ref):
                    ids_selectionnes.append(feature.id())
                    id_mnhn = feature["id_mnhn"]
                    if id_mnhn:
                        liste_stockage.append(str(id_mnhn))

            if ids_selectionnes:
                couche_source.selectByIds(ids_selectionnes)
                self.log(
                    f"{len(ids_selectionnes)} entités sélectionnées dans '{couche_source.name()}'",
                    Qgis.Info
                )
            else:
                self.log(
                    f"Aucune entité sélectionnée dans '{couche_source.name()}'",
                    Qgis.Warning
                )

        except Exception as e:
            self.log(f"Erreur lors de la sélection spatiale : {str(e)}", Qgis.Critical)

    def download_file(self, url: str, save_path: str, retries: int = 3) -> bool:
        """Télécharge un fichier XML avec retry exponentiel."""
        attempt = 0
        while attempt < retries:
            try:
                self.log(f"Tentative {attempt + 1}/{retries} : {url}", Qgis.Info)
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                with open(save_path, 'wb') as f:
                    f.write(response.content)

                self.files_downloaded += 1
                self.log(f"Téléchargé : {os.path.basename(save_path)}", Qgis.Success)
                return True

            except requests.exceptions.RequestException as e:
                attempt += 1
                wait_time = 2 ** attempt
                self.log(f"Échec tentative {attempt} : {str(e)}", Qgis.Warning)
                time.sleep(wait_time)

        self.log(f"Échec après {retries} tentatives : {url}", Qgis.Critical)
        return False

    def execute_download(self) -> bool:
        """Exécute la sélection spatiale puis le téléchargement de tous les fichiers XML."""
        self.ids_1.clear()
        self.ids_2.clear()
        self.files_downloaded = 0

        self.selectionner_et_stocker(self.patrinat_layer_1, self.ids_1)
        self.selectionner_et_stocker(self.patrinat_layer_2, self.ids_2)

        all_ids = self.ids_1 + self.ids_2
        total = len(all_ids)

        if total == 0:
            self.log("Aucun site intersectant la zone d'étude", Qgis.Warning)
            return False

        self.log(f"{total} fichiers à télécharger", Qgis.Info)
        success_count = 0

        for i, zone_id in enumerate(all_ids):
            if (i + 1) % 5 == 0 or i == 0 or i == total - 1:
                self.log(f"Progression : {i + 1}/{total}", Qgis.Info)

            url = self.build_url(zone_id)
            save_path = os.path.join(self.download_folder, f"{zone_id}.xml")

            if self.download_file(url, save_path):
                success_count += 1

        if success_count > 0:
            self.log(
                f"Téléchargement terminé — {success_count}/{total} fichiers téléchargés",
                Qgis.Success
            )
            return True
        else:
            self.log("Échec du téléchargement", Qgis.Critical)
            return False

    def log(self, message: str, level=Qgis.Info):
        """Enregistre un message dans le journal QGIS."""
        QgsMessageLog.logMessage(
            f"[{self.__class__.__name__}]: {message}",
            "Biblizou",
            level=level
        )
