# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : ZnieffXmlToLayerHab.py
Groupe : FSD
Description : Module pour extraire des données d'habitats déterminants à partir de fichiers XML ZNIEFF
              et les exporter dans un GeoPackage.
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


class ZnieffXmlToLayerHab:
    def __init__(self):
        """Initialisation de la classe."""
        self.total_habitats = 0
        self.processed_files = 0
        self.gpkg_path = None
        self.gpkg_saved = False
        
    def run(self):
        """Point d'entrée principal du module (mode indépendant avec boîte de dialogue)."""
        # 1. Sélection du dossier via boîte de dialogue
        folder_path = self.select_folder_dialog()
        if not folder_path:
            return
            
        # 2. Traitement des fichiers
        habitats_data = self.process_folder(folder_path)
        
        if not habitats_data:
            QMessageBox.information(
                None, 
                "Information", 
                "Aucun habitat déterminant trouvé dans les fichiers XML."
            )
            return
            
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
            QgsMessageLog.logMessage(
                "ZnieffXmlToLayerHab: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
                "Biblizou", 
                level=Qgis.Warning
            )
        
        # 6. Résumé
        self.show_summary(len(habitats_data))
    
    def run_with_path(self, folder_path):
        """
        Point d'entrée pour BiblizouMain (sans boîte de dialogue).
        
        Args:
            folder_path (str): Chemin du dossier contenant les fichiers XML
        Returns:
            bool: True si le traitement a réussi, False sinon
        """
        if not folder_path:
            QgsMessageLog.logMessage(
                "ZnieffXmlToLayerHab: Aucun dossier spécifié", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        if not os.path.isdir(folder_path):
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Dossier introuvable: {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        try:
            # 1. Traitement des fichiers
            habitats_data = self.process_folder(folder_path)
            
            if not habitats_data:
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerHab: Aucun habitat trouvé dans {folder_path}", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
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
                QgsMessageLog.logMessage(
                    "ZnieffXmlToLayerHab: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
            
            # 5. Log du résumé
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Traitement terminé - "
                f"{self.processed_files} fichiers, {len(habitats_data)} habitats", 
                "Biblizou", 
                level=Qgis.Success
            )
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Erreur lors du traitement: {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
            return False
        
    def select_folder_dialog(self):
        """Sélectionne un dossier via boîte de dialogue (mode indépendant)."""
        folder_path, ok = QInputDialog.getText(
            None,
            "Sélection du dossier",
            "Entrez le chemin du dossier contenant les fichiers XML ZNIEFF :"
        )
        
        if not ok or not folder_path:
            QgsMessageLog.logMessage(
                "ZnieffXmlToLayerHab: Annulation par l'utilisateur", 
                "Biblizou", 
                level=Qgis.Info
            )
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
        
        # Filtrer les fichiers XML ZNIEFF (non FR, 13 caractères)
        xml_files = [
            f for f in os.listdir(folder_path) 
            if f.endswith('.xml') and not f.startswith('FR') and len(f) == 13
        ]
        
        if not xml_files:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Aucun fichier XML ZNIEFF trouvé dans {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return []
            
        QgsMessageLog.logMessage(
            f"ZnieffXmlToLayerHab: {len(xml_files)} fichiers XML à traiter", 
            "Biblizou", 
            level=Qgis.Info
        )
        
        # Traiter chaque fichier
        for i, xml_file in enumerate(xml_files, 1):
            full_path = os.path.join(folder_path, xml_file)
            file_habitats = self.process_xml_file(full_path)
            
            if file_habitats:
                habitats_data.extend(file_habitats)
                self.processed_files += 1
                
            # Log de progression
            if i % 10 == 0 or i == len(xml_files):
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerHab: Progression: {i}/{len(xml_files)} fichiers traités "
                    f"({len(file_habitats)} habitats)", 
                    "Biblizou", 
                    level=Qgis.Info
                )
                
        self.total_habitats = len(habitats_data)
        return habitats_data
        
    def process_xml_file(self, xml_path):
        """
        Traite un fichier XML ZNIEFF individuel.
        Logique adaptée strictement de 14_znieff_xml2xlsx_hab.py pour garantir l'extraction.
        """
        habitats_data = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Boucle sur les éléments ZNIEFF (comme dans le script fonctionnel)
            for znieff_elem in root.iter('ZNIEFF'):
                nm_sffzn = ""
                lb_zn = ""
                
                # Extraction des métadonnées de la ZNIEFF
                nm_sffzn_elem = znieff_elem.find('NM_SFFZN')
                lb_zn_elem = znieff_elem.find('LB_ZN')
                
                if nm_sffzn_elem is not None:
                    nm_sffzn = nm_sffzn_elem.text
                    
                if lb_zn_elem is not None:
                    lb_zn = lb_zn_elem.text
                    
                # Itération à travers les éléments TYPO_INFO_ROW
                for typo_info_row_elem in znieff_elem.iter('TYPO_INFO_ROW'):
                    fg_typo_elem = typo_info_row_elem.find('FG_TYPO')
                    
                    # On ne considère que LB_CODE et LB_HAB si FG_TYPO vaut 'D'
                    if fg_typo_elem is not None and fg_typo_elem.text == 'D':
                        
                        codes_in_row = []
                        habs_in_row = []
                        
                        # Utilisation stricte de .iter() comme dans le vieux script
                        for lb_code_elem in typo_info_row_elem.iter('LB_CODE'):
                            if lb_code_elem.text:
                                codes_in_row.append(lb_code_elem.text)
                                
                        for lb_hab_elem in typo_info_row_elem.iter('LB_HAB'):
                            if lb_hab_elem.text:
                                habs_in_row.append(lb_hab_elem.text)
                        
                        # Création des paires
                        max_len = max(len(codes_in_row), len(habs_in_row))
                        
                        for i in range(max_len):
                            code = codes_in_row[i] if i < len(codes_in_row) else ""
                            hab = habs_in_row[i] if i < len(habs_in_row) else ""
                            
                            habitat_data = {
                                'NM_SFFZN': nm_sffzn,
                                'LB_ZN': lb_zn,
                                'LB_CODE': code,
                                'LB_HAB': hab
                            }
                            habitats_data.append(habitat_data)

        except ET.ParseError as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Erreur de parsing XML {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Erreur traitement {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            
        return habitats_data
        
    def create_temp_layer(self, habitats_data):
        """Crée une couche temporaire QGIS sans géométrie avec les données d'habitats ZNIEFF."""
        # Définir les champs
        fields = [
            QgsField('NM_SFFZN', QVariant.String),  # Numéro ZNIEFF
            QgsField('LB_ZN', QVariant.String),     # Nom ZNIEFF
            QgsField('LB_CODE', QVariant.String),   # Code habitat
            QgsField('LB_HAB', QVariant.String)     # Libellé habitat
        ]
        
        # Créer la couche (sans géométrie)
        layer = QgsVectorLayer("None", "Znieff_Habitats_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        
        # Ajouter les features
        features = []
        for data in habitats_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([
                data.get('NM_SFFZN', ''),
                data.get('LB_ZN', ''),
                data.get('LB_CODE', ''),
                data.get('LB_HAB', '')
            ])
            features.append(feat)
            
        provider.addFeatures(features)
        layer.updateExtents()
        
        QgsMessageLog.logMessage(
            f"ZnieffXmlToLayerHab: Couche temporaire créée avec {len(habitats_data)} entrées", 
            "Biblizou", 
            level=Qgis.Info
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
            save_options.layerName = "Znieff_Habitats"
            
            if gpkg_exists:
                # Le fichier existe : on ajoute/remplace la couche
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerHab: GeoPackage existant trouvé : {self.gpkg_path}", 
                    "Biblizou", 
                    level=Qgis.Info
                )
            else:
                # Le fichier n'existe pas : on le crée
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerHab: Création d'un nouveau GeoPackage : {self.gpkg_path}", 
                    "Biblizou", 
                    level=Qgis.Info
                )
            
            # Écriture dans le GeoPackage
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                self.gpkg_path,
                QgsProject.instance().transformContext(),
                save_options
            )
            
            if error[0] == QgsVectorFileWriter.NoError:
                self.gpkg_saved = True
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerHab: Couche sauvegardée avec succès dans {self.gpkg_path}", 
                    "Biblizou", 
                    level=Qgis.Success
                )
            else:
                self.gpkg_saved = False
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerHab: Erreur lors de la sauvegarde : {error[1]}", 
                    "Biblizou", 
                    level=Qgis.Critical
                )
                
        except Exception as e:
            self.gpkg_saved = False
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Exception lors de la sauvegarde : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
    
    def load_from_geopackage(self):
        """Charge la couche depuis le GeoPackage dans QGIS."""
        try:
            # Construire l'URI pour charger la couche depuis le GeoPackage
            uri = f"{self.gpkg_path}|layername=Znieff_Habitats"
            layer = QgsVectorLayer(uri, "Znieff_Habitats", "ogr")
            
            if layer.isValid():
                # Supprimer l'ancienne couche si elle existe déjà dans le projet
                existing_layers = QgsProject.instance().mapLayersByName("Znieff_Habitats")
                for existing_layer in existing_layers:
                    QgsProject.instance().removeMapLayer(existing_layer.id())
                
                # Ajouter la nouvelle couche
                QgsProject.instance().addMapLayer(layer)
                QgsMessageLog.logMessage(
                    "ZnieffXmlToLayerHab: Couche chargée depuis le GeoPackage", 
                    "Biblizou", 
                    level=Qgis.Success
                )
            else:
                QgsMessageLog.logMessage(
                    "ZnieffXmlToLayerHab: Erreur - la couche chargée n'est pas valide", 
                    "Biblizou", 
                    level=Qgis.Critical
                )
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerHab: Erreur lors du chargement : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
        
    def show_summary(self, habitats_count):
        """Affiche un résumé du traitement (mode indépendant uniquement)."""
        gpkg_status = "✓ Sauvegardé avec succès" if self.gpkg_saved else "✗ Échec de sauvegarde (couche temporaire chargée)"
        
        summary = (
            f"Résultats du traitement ZNIEFF - Habitats:\n\n"
            f"• Fichiers XML traités: {self.processed_files}\n"
            f"• Habitats déterminants extraits: {habitats_count}\n"
            f"• Champs extraits: 4 champs complets\n\n"
            f"GeoPackage: {gpkg_status}\n"
            f"Chemin: {self.gpkg_path}\n\n"
            f"✓ Couche 'Znieff_Habitats' chargée dans QGIS\n"
            f"✓ Données complètes avec tous les champs ZNIEFF"
        )
            
        QMessageBox.information(
            None,
            "Traitement ZNIEFF terminé",
            summary
        )


# Pour exécuter le module dans QGIS
def run_module():
    """Fonction d'exécution pour QGIS (mode indépendant)."""
    module = ZnieffXmlToLayerHab()
    module.run()


def run_module_with_path(folder_path):
    """
    Fonction d'exécution pour BiblizouMain.
    
    Args:
        folder_path (str): Chemin du dossier contenant les fichiers XML
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    module = ZnieffXmlToLayerHab()
    return module.run_with_path(folder_path)


# Exécution
if __name__ == "__console__":
    # Mode console: exécuter en mode indépendant
    run_module()