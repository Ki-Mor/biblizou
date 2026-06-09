# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : ZnieffDwlXml.py
Groupe : FSD
Description : Module pour télécharger les xml des zonages ZNIEFF dans un périmètre donné.
              Version compatible avec BiblizouMain ou exécution indépendante.
"""

import os
import requests
import time
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeatureRequest,
    QgsMessageLog,
    QgsCoordinateTransform,
    QgsGeometry,
    Qgis
)
from PyQt5.QtWidgets import QInputDialog, QMessageBox


class ZnieffDwlXml:
    def __init__(self):
        """Initialisation de la classe."""
        # Recherche des couches Patrinat dans le projet
        self.patrinat_zn1 = None
        self.patrinat_zn2 = None
        
        # Variables pour le traitement
        self.id_mnhn_zn1 = []
        self.id_mnhn_zn2 = []
        self.ae_eloignee = None
        self.download_folder = None
        self.files_downloaded = 0
        
    def run(self):
        """Point d'entrée principal du module (mode indépendant avec boîtes de dialogue)."""
        # 1. Rechercher les couches Patrinat
        if not self.find_patrinat_layers():
            return
            
        # 2. Sélection de la couche de référence
        if not self.select_layer_dialog():
            return
            
        # 3. Sélection du dossier de téléchargement
        if not self.select_download_folder_dialog():
            return
            
        # 4. Exécution du téléchargement
        success = self.execute_download()
        
        # 5. Affichage du résumé
        if success:
            self.show_summary()
    
    def run_with_params(self, znieff_layer, folder_path):
        """
        Point d'entrée pour BiblizouMain (sans boîtes de dialogue).
        
        Args:
            znieff_layer (QgsVectorLayer): Couche ZNIEFF de référence
            folder_path (str): Chemin du dossier de téléchargement
        Returns:
            bool: True si le téléchargement a réussi, False sinon
        """
        try:
            # Rechercher les couches Patrinat
            if not self.find_patrinat_layers():
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Couches Patrinat ZNIEFF1 ou ZNIEFF2 introuvables",
                    "Biblizou",
                    level=Qgis.Warning
                )
                return False
                
            # Définir les paramètres
            self.ae_eloignee = znieff_layer
            self.download_folder = folder_path
            
            # Vérifier les paramètres
            if not self.ae_eloignee:
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Couche ZNIEFF de référence non définie",
                    "Biblizou",
                    level=Qgis.Warning
                )
                return False
                
            if not os.path.isdir(self.download_folder):
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Dossier introuvable: {self.download_folder}",
                    "Biblizou",
                    level=Qgis.Warning
                )
                return False
                
            # Exécuter le téléchargement
            return self.execute_download()
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffDwlXml: Erreur lors du téléchargement: {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )
            return False
    
    def find_patrinat_layers(self):
        """Recherche les couches Patrinat dans le projet."""
        try:
            # Recherche des couches Patrinat
            zn1_layers = QgsProject.instance().mapLayersByName("Patrinat : ZNIEFF1")
            zn2_layers = QgsProject.instance().mapLayersByName("Patrinat : ZNIEFF2")
            
            if zn1_layers:
                self.patrinat_zn1 = zn1_layers[0]
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Couche Patrinat ZNIEFF1 trouvée",
                    "Biblizou",
                    level=Qgis.Info
                )
            else:
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Couche Patrinat ZNIEFF1 introuvable",
                    "Biblizou",
                    level=Qgis.Warning
                )
                
            if zn2_layers:
                self.patrinat_zn2 = zn2_layers[0]
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Couche Patrinat ZNIEFF2 trouvée",
                    "Biblizou",
                    level=Qgis.Info
                )
            else:
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Couche Patrinat ZNIEFF2 introuvable",
                    "Biblizou",
                    level=Qgis.Warning
                )
                
            return self.patrinat_zn1 is not None and self.patrinat_zn2 is not None
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffDwlXml: Erreur lors de la recherche des couches Patrinat: {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )
            return False
    
    def select_layer_dialog(self):
        """Sélectionne une couche via boîte de dialogue (mode indépendant)."""
        try:
            layers = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
            
            if not layers:
                QMessageBox.warning(
                    None,
                    "Erreur",
                    "Aucune couche disponible dans le projet."
                )
                return False
                
            selected_layer, ok = QInputDialog.getItem(
                None,
                "Sélection de la couche",
                "Choisissez une couche de référence :",
                layers,
                0,
                False
            )
            
            if not ok or not selected_layer:
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Annulation par l'utilisateur (sélection de couche)",
                    "Biblizou",
                    level=Qgis.Info
                )
                return False
                
            selected_layers = QgsProject.instance().mapLayersByName(selected_layer)
            
            if selected_layers:
                self.ae_eloignee = selected_layers[0]
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Couche sélectionnée: {selected_layer}",
                    "Biblizou",
                    level=Qgis.Info
                )
                return True
            else:
                QMessageBox.warning(
                    None,
                    "Erreur",
                    f"La couche '{selected_layer}' est introuvable."
                )
                return False
                
        except Exception as e:
            QMessageBox.critical(
                None,
                "Erreur",
                f"Erreur lors de la sélection de la couche: {str(e)}"
            )
            return False
    
    def select_download_folder_dialog(self):
        """Sélectionne un dossier via boîte de dialogue (mode indépendant)."""
        try:
            download_folder, ok = QInputDialog.getText(
                None,
                "Chemin vers le dossier de travail",
                "Copier/coller le chemin du dossier de téléchargement :"
            )
            
            if not ok or not download_folder:
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Annulation par l'utilisateur (sélection de dossier)",
                    "Biblizou",
                    level=Qgis.Info
                )
                return False
                
            if not os.path.isdir(download_folder):
                QMessageBox.warning(
                    None,
                    "Erreur",
                    f"Le dossier '{download_folder}' n'existe pas."
                )
                return False
                
            self.download_folder = download_folder
            QgsMessageLog.logMessage(
                f"ZnieffDwlXml: Dossier sélectionné: {download_folder}",
                "Biblizou",
                level=Qgis.Info
            )
            return True
            
        except Exception as e:
            QMessageBox.critical(
                None,
                "Erreur",
                f"Erreur lors de la sélection du dossier: {str(e)}"
            )
            return False
    
    def selectionner_et_stocker(self, couche_source, liste_stockage):
        """Sélectionne les entités intersectant AE_eloignee et stocke leurs ID."""
        if not couche_source or not self.ae_eloignee:
            QgsMessageLog.logMessage(
                f"ZnieffDwlXml: Couche source ou AE_eloignee introuvable",
                "Biblizou",
                level=Qgis.Warning
            )
            return
        
        try:
            # Définir la transformation de coordonnées
            transform = QgsCoordinateTransform(
                self.ae_eloignee.crs(),
                couche_source.crs(),
                QgsProject.instance()
            )
            
            # Fusionner toutes les géométries de AE_eloignee en une seule
            geometries = [f.geometry() for f in self.ae_eloignee.getFeatures()]
            
            if not geometries:
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Aucune géométrie trouvée dans AE_eloignee",
                    "Biblizou",
                    level=Qgis.Warning
                )
                return
            
            geom_ref = QgsGeometry.unaryUnion(geometries)
            geom_ref.transform(transform)
            
            couche_source.removeSelection()
            ids_selectionnes = []
            liste_stockage.clear()
            
            # Effectuer une sélection spatiale
            request = QgsFeatureRequest().setFilterRect(geom_ref.boundingBox())
            
            for feature in couche_source.getFeatures(request):
                if feature.geometry().intersects(geom_ref):
                    ids_selectionnes.append(feature.id())
                    id_mnhn = feature["id_mnhn"]
                    if id_mnhn:
                        liste_stockage.append(str(id_mnhn))
            
            if ids_selectionnes:
                couche_source.selectByIds(ids_selectionnes)
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: {len(ids_selectionnes)} entités sélectionnées dans {couche_source.name()}",
                    "Biblizou",
                    level=Qgis.Info
                )
            else:
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Aucune entité sélectionnée dans {couche_source.name()}",
                    "Biblizou",
                    level=Qgis.Warning
                )
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffDwlXml: Erreur lors de la sélection: {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )
    
    def download_file(self, url, save_path, retries=3):
        """Télécharge un fichier XML avec gestion des erreurs."""
        attempt = 0
        while attempt < retries:
            try:
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Tentative {attempt + 1} pour {url}",
                    "Biblizou",
                    level=Qgis.Info
                )
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                    
                self.files_downloaded += 1
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Fichier téléchargé avec succès: {save_path}",
                    "Biblizou",
                    level=Qgis.Success
                )
                return True
                
            except requests.exceptions.RequestException as e:
                attempt += 1
                wait_time = 2 ** attempt
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Échec tentative {attempt} pour {url}: {str(e)}",
                    "Biblizou",
                    level=Qgis.Warning
                )
                time.sleep(wait_time)
                
        QgsMessageLog.logMessage(
            f"ZnieffDwlXml: Échec du téléchargement après {retries} tentatives: {url}",
            "Biblizou",
            level=Qgis.Critical
        )
        return False
    
    def construct_url_and_download(self, znieff_ids):
        """Construit les URLs et télécharge les fichiers XML correspondants."""
        if not znieff_ids:
            QgsMessageLog.logMessage(
                "ZnieffDwlXml: Aucun identifiant ZNIEFF trouvé",
                "Biblizou",
                level=Qgis.Warning
            )
            return False
        
        total_ids = len(znieff_ids)
        success_count = 0
        
        for i, znieff_id in enumerate(znieff_ids):
            # Log de progression
            if (i + 1) % 5 == 0 or i == 0 or i == total_ids - 1:
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Progression: {i + 1}/{total_ids}",
                    "Biblizou",
                    level=Qgis.Info
                )
            
            url = f"https://inpn.mnhn.fr/docs/ZNIEFF/znieffxml/{znieff_id}.xml"
            save_path = os.path.join(self.download_folder, f"{znieff_id}.xml")
            
            if self.download_file(url, save_path):
                success_count += 1
        
        return success_count > 0
    
    def execute_download(self):
        """Exécute le processus complet de téléchargement."""
        try:
            # Réinitialiser les compteurs
            self.id_mnhn_zn1.clear()
            self.id_mnhn_zn2.clear()
            self.files_downloaded = 0
            
            # Sélectionner et stocker les IDs
            self.selectionner_et_stocker(self.patrinat_zn1, self.id_mnhn_zn1)
            self.selectionner_et_stocker(self.patrinat_zn2, self.id_mnhn_zn2)
            
            total_ids = len(self.id_mnhn_zn1) + len(self.id_mnhn_zn2)
            
            if total_ids == 0:
                QgsMessageLog.logMessage(
                    "ZnieffDwlXml: Aucun site ZNIEFF intersectant la zone d'étude",
                    "Biblizou",
                    level=Qgis.Warning
                )
                return False
            
            QgsMessageLog.logMessage(
                f"ZnieffDwlXml: {total_ids} fichiers à télécharger",
                "Biblizou",
                level=Qgis.Info
            )
            
            # Télécharger les fichiers
            all_ids = self.id_mnhn_zn1 + self.id_mnhn_zn2
            success = self.construct_url_and_download(all_ids)
            
            if success:
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Téléchargement terminé - {self.files_downloaded}/{total_ids} fichiers téléchargés",
                    "Biblizou",
                    level=Qgis.Success
                )
            else:
                QgsMessageLog.logMessage(
                    f"ZnieffDwlXml: Échec du téléchargement",
                    "Biblizou",
                    level=Qgis.Critical
                )
            
            return success
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffDwlXml: Erreur lors de l'exécution: {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )
            return False
    
    def show_summary(self):
        """Affiche un résumé du téléchargement (mode indépendant uniquement)."""
        total_ids = len(self.id_mnhn_zn1) + len(self.id_mnhn_zn2)
        
        summary = (
            f"Résultats du téléchargement ZNIEFF:\n\n"
            f"• Sites ZNIEFF1 intersectants: {len(self.id_mnhn_zn1)}\n"
            f"• Sites ZNIEFF2 intersectants: {len(self.id_mnhn_zn2)}\n"
            f"• Total des fichiers: {total_ids}\n"
            f"• Fichiers téléchargés: {self.files_downloaded}\n\n"
            f"Dossier: {self.download_folder}\n\n"
            f"✓ Les fichiers XML sont prêts pour le traitement"
        )
        
        QMessageBox.information(
            None,
            "Téléchargement ZNIEFF terminé",
            summary
        )


# Pour exécuter le module dans QGIS
def run_module():
    """Fonction d'exécution pour QGIS (mode indépendant)."""
    module = ZnieffDwlXml()
    module.run()


def run_module_with_params(znieff_layer, folder_path):
    """
    Fonction d'exécution pour BiblizouMain.
    
    Args:
        znieff_layer (QgsVectorLayer): Couche ZNIEFF de référence
        folder_path (str): Chemin du dossier de téléchargement
    Returns:
        bool: True si le téléchargement a réussi, False sinon
    """
    module = ZnieffDwlXml()
    return module.run_with_params(znieff_layer, folder_path)


# Exécution
if __name__ == "__console__":
    # Mode console: exécuter en mode indépendant
    run_module()