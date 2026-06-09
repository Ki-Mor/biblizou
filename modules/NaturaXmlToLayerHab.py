# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaXmlToLayerHab.py
Groupe : FSD
Description : Module pour extraire des données d'habitats directive à partir de fichiers XML
              et les exporter dans un GeoPackage.
              Version compatible avec BiblizouMain ou exécution indépendante.
"""

import os
import xml.etree.ElementTree as ET
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsMessageLog,
    QgsVectorFileWriter,
    Qgis
)
from qgis.PyQt.QtCore import QVariant
from PyQt5.QtWidgets import QInputDialog, QMessageBox

class NaturaXmlToLayerHab:
    def __init__(self):
        """Initialisation de la classe."""
        self.processed_files = 0
        self.total_habitats = 0
        self.gpkg_path = None
        self.gpkg_saved = False
        
    def run(self):
        """Point d'entrée principal du module (mode indépendant avec boîte de dialogue)."""
        # 1. Sélection du dossier via boîte de dialogue
        folder_path = self.select_folder_dialog()
        if not folder_path:
            return False
            
        # 2. Traitement des fichiers
        habitats_data = self.process_folder(folder_path)
        
        if not habitats_data:
            QMessageBox.information(
                None, 
                "Information", 
                "Aucune donnée d'habitat trouvée dans les fichiers XML."
            )
            return True  # Ce n'est pas une erreur fatale
            
        # 3. Création de la couche temporaire
        temp_layer = self.create_temp_layer(habitats_data)
        
        # 4. Enregistrement dans GeoPackage
        self.gpkg_path = os.path.join(folder_path, "biblizou.gpkg")
        self.save_to_geopackage(temp_layer)
        
        # 5. Chargement de la couche depuis le GeoPackage
        if self.gpkg_saved:
            self.load_from_geopackage()
        else:
            # Solution de secours : ajouter la couche temporaire
            QgsProject.instance().addMapLayer(temp_layer)
            self.log_message(
                "Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
                Qgis.Warning
            )
        
        # 6. Résumé
        self.show_summary(len(habitats_data))
        return True
    
    def run_with_path(self, folder_path):
        """
        Point d'entrée pour BiblizouMain (sans boîte de dialogue).
        
        Args:
            folder_path (str): Chemin du dossier contenant les fichiers XML
        Returns:
            bool: True si le traitement a réussi, False sinon
        """
        if not folder_path:
            self.log_message("Aucun dossier spécifié", Qgis.Warning)
            return False
            
        if not os.path.isdir(folder_path):
            self.log_message(f"Dossier introuvable: {folder_path}", Qgis.Warning)
            return False
            
        try:
            # 1. Traitement des fichiers
            habitats_data = self.process_folder(folder_path)
            
            if not habitats_data:
                self.log_message(f"Aucun habitat trouvé dans {folder_path}", Qgis.Warning)
                # Ce n'est pas une erreur fatale, on retourne True quand même
                return None
                
            # 2. Création de la couche temporaire
            temp_layer = self.create_temp_layer(habitats_data)
            
            # 3. Enregistrement dans GeoPackage
            self.gpkg_path = os.path.join(folder_path, "biblizou.gpkg")
            self.save_to_geopackage(temp_layer)
            
            # 4. Chargement de la couche depuis le GeoPackage
            if self.gpkg_saved:
                self.load_from_geopackage()
            else:
                # Solution de secours : ajouter la couche temporaire
                QgsProject.instance().addMapLayer(temp_layer)
                self.log_message(
                    "Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
                    Qgis.Warning
                )
            
            # 5. Log du résumé
            self.log_message(
                f"Traitement terminé - {self.processed_files} fichiers, {len(habitats_data)} habitats", 
                Qgis.Success
            )
            
            return True
            
        except Exception as e:
            self.log_message(f"Erreur lors du traitement: {str(e)}", Qgis.Critical)
            return False
        
    def select_folder_dialog(self):
        """Sélectionne un dossier via boîte de dialogue (mode indépendant uniquement)."""
        folder_path, ok = QInputDialog.getText(
            None,
            "Sélection du dossier",
            "Entrez le chemin du dossier contenant les fichiers XML Natura 2000 :"
        )
        
        if not ok or not folder_path:
            self.log_message("Annulation par l'utilisateur", Qgis.Info)
            return None
            
        if not os.path.isdir(folder_path):
            QMessageBox.warning(
                None, 
                "Erreur", 
                f"Le dossier '{folder_path}' n'existe pas."
            )
            return None
            
        return folder_path
        
    def process_folder(self, folder_path):
        """
        Traite tous les fichiers XML du dossier.
        Retourne: liste de dictionnaires d'habitats
        """
        habitats_data = []
        
        # Filtrer les fichiers FR*.xml (13 caractères)
        xml_files = [
            f for f in os.listdir(folder_path) 
            if f.startswith('FR') and f.endswith('.xml') and len(f) == 13
        ]
        
        if not xml_files:
            self.log_message("Aucun fichier XML Natura 2000 trouvé dans le dossier", Qgis.Warning)
            return []
            
        self.log_message(f"{len(xml_files)} fichiers XML à traiter", Qgis.Info)
        
        # Traiter chaque fichier
        for i, xml_file in enumerate(xml_files, 1):
            full_path = os.path.join(folder_path, xml_file)
            file_habitats = self.process_xml_file(full_path)
            
            if file_habitats:
                habitats_data.extend(file_habitats)
                self.processed_files += 1
                
            # Log de progression
            if i % 10 == 0 or i == len(xml_files):
                self.log_message(
                    f"Progression: {i}/{len(xml_files)} fichiers traités", 
                    Qgis.Info
                )
                
        self.total_habitats = len(habitats_data)
        return habitats_data
        
    def process_xml_file(self, xml_path):
        """Traite un fichier XML individuel."""
        habitats_data = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extraire les informations du site
            sitecode_elem = root.find('SITECODE')
            site_name_elem = root.find('SITE_NAME')
            
            sitecode = sitecode_elem.text.strip() if sitecode_elem is not None and sitecode_elem.text else ""
            site_name = site_name_elem.text.strip() if site_name_elem is not None and site_name_elem.text else ""
            
            # Chercher les habitats dans HABIT1_ROW
            for habit1_row in root.findall('.//HABIT1_ROW'):
                cd_hab_elem = habit1_row.find('CD_UE')
                lb_habdh_fr_elem = habit1_row.find('LB_HABDH_FR')
                
                if cd_hab_elem is not None and lb_habdh_fr_elem is not None:
                    cd_hab = cd_hab_elem.text.strip() if cd_hab_elem.text else ""
                    lb_habdh_fr = lb_habdh_fr_elem.text.strip() if lb_habdh_fr_elem.text else ""
                    
                    # Préparer les données de l'habitat
                    habitat_data = {
                        'SITECODE': sitecode,
                        'SITE_NAME': site_name,
                        'CD_UE': cd_hab,
                        'LB_HABDH_FR': lb_habdh_fr
                    }
                    
                    habitats_data.append(habitat_data)
                        
        except ET.ParseError as e:
            self.log_message(
                f"Erreur de parsing XML {os.path.basename(xml_path)}: {str(e)}", 
                Qgis.Warning
            )
        except Exception as e:
            self.log_message(
                f"Erreur traitement {os.path.basename(xml_path)}: {str(e)}", 
                Qgis.Warning
            )
            
        return habitats_data
        
    def create_temp_layer(self, habitats_data):
        """Crée une couche temporaire QGIS sans géométrie avec les données d'habitats."""
        # Définir les champs
        fields = [
            QgsField('SITECODE', QVariant.String),
            QgsField('SITE_NAME', QVariant.String),
            QgsField('CD_UE', QVariant.String),
            QgsField('LB_HABDH_FR', QVariant.String)
        ]
        
        # Créer la couche (sans géométrie)
        layer = QgsVectorLayer("None", "Natura_2000_Habitats_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        
        # Ajouter les features
        features = []
        for data in habitats_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([
                data.get('SITECODE', ''),
                data.get('SITE_NAME', ''),
                data.get('CD_UE', ''),
                data.get('LB_HABDH_FR', '')
            ])
            features.append(feat)
            
        provider.addFeatures(features)
        layer.updateExtents()
        
        self.log_message(
            f"Couche temporaire créée avec {len(habitats_data)} entrées", 
            Qgis.Info
        )
        
        return layer
        
    def save_to_geopackage(self, layer):
        """Enregistre la couche dans un GeoPackage."""
        try:
            # Vérifier si le GeoPackage existe déjà
            gpkg_exists = os.path.exists(self.gpkg_path)
            
            # Options de sauvegarde
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.driverName = "GPKG"
            save_options.layerName = "Natura_2000_Habitats"
            
            if gpkg_exists:
                # Le fichier existe : on ajoute/remplace la couche
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                self.log_message(f"GeoPackage existant trouvé : {self.gpkg_path}", Qgis.Info)
            else:
                # Le fichier n'existe pas : on le crée
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                self.log_message(f"Création d'un nouveau GeoPackage : {self.gpkg_path}", Qgis.Info)
            
            # Écriture dans le GeoPackage
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                self.gpkg_path,
                QgsProject.instance().transformContext(),
                save_options
            )
            
            if error[0] == QgsVectorFileWriter.NoError:
                self.gpkg_saved = True
                self.log_message(f"Couche sauvegardée avec succès dans {self.gpkg_path}", Qgis.Success)
            else:
                self.gpkg_saved = False
                self.log_message(f"Erreur lors de la sauvegarde : {error[1]}", Qgis.Critical)
                
        except Exception as e:
            self.gpkg_saved = False
            self.log_message(f"Exception lors de la sauvegarde : {str(e)}", Qgis.Critical)
    
    def load_from_geopackage(self):
        """Charge la couche depuis le GeoPackage dans QGIS."""
        try:
            # Construire l'URI pour charger la couche depuis le GeoPackage
            uri = f"{self.gpkg_path}|layername=Natura_2000_Habitats"
            layer = QgsVectorLayer(uri, "Natura_2000_Habitats", "ogr")
            
            if layer.isValid():
                # Supprimer l'ancienne couche si elle existe déjà dans le projet
                existing_layers = QgsProject.instance().mapLayersByName("Natura_2000_Habitats")
                for existing_layer in existing_layers:
                    QgsProject.instance().removeMapLayer(existing_layer.id())
                
                # Ajouter la nouvelle couche
                QgsProject.instance().addMapLayer(layer)
                self.log_message("Couche chargée depuis le GeoPackage", Qgis.Success)
            else:
                self.log_message("Erreur : la couche chargée n'est pas valide", Qgis.Critical)
                
        except Exception as e:
            self.log_message(f"Erreur lors du chargement : {str(e)}", Qgis.Critical)
        
    def show_summary(self, habitats_count):
        """Affiche un résumé du traitement (mode indépendant uniquement)."""
        gpkg_status = "✓ Sauvegardé avec succès" if self.gpkg_saved else "✗ Échec de sauvegarde (couche temporaire chargée)"
        
        summary = (
            f"Résultats du traitement Natura 2000 - Habitats:\n\n"
            f"• Fichiers XML traités: {self.processed_files}\n"
            f"• Habitats extraits: {habitats_count}\n\n"
            f"GeoPackage: {gpkg_status}\n"
            f"Chemin: {self.gpkg_path}\n\n"
            f"✓ Couche 'Natura_2000_Habitats' chargée dans QGIS"
        )
            
        QMessageBox.information(
            None,
            "Traitement terminé",
            summary
        )
    
    def log_message(self, message, level=Qgis.Info):
        """Enregistre un message avec le préfixe du module."""
        full_message = f"[NaturaXmlToLayerHab]: {message}"
        QgsMessageLog.logMessage(full_message, "Biblizou", level=level)


# Pour exécuter le module dans QGIS
def run_module():
    """Fonction d'exécution pour QGIS (mode indépendant)."""
    module = NaturaXmlToLayerHab()
    module.run()


def run_module_with_path(folder_path):
    """
    Fonction d'exécution pour BiblizouMain.
    
    Args:
        folder_path (str): Chemin du dossier contenant les fichiers XML
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    module = NaturaXmlToLayerHab()
    return module.run_with_path(folder_path)


# Exécution
if __name__ == "__console__":
    # Mode console: exécuter en mode indépendant
    run_module()