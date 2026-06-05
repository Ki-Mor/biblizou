"""
Auteur : ExEco Environnement - François Botcazou
Date : 2025/03
Version : 1.3
Nom : ZnieffXmlToLayerEsp.py
Groupe : Biblizou_PatNat
Description : Module pour extraire les données d'espèces à partir des XML ZNIEFF
              et les exporter dans un GeoPackage (Mode Offline).
              Version compatible avec BiblizouMain ou exécution indépendante.
Dépendances :
    - Python 3.x
    - QGIS (QgsVectorLayer, QgsField, QgsFeature, QgsMessageLog)
    - xml.etree.ElementTree

Utilisation :
    - En mode BiblizouMain : module.run_with_path(folder_path)
    - En mode indépendant : module.run() (ouvre une boîte de dialogue)
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


class ZnieffXmlToLayerEsp:
    def __init__(self):
        """Initialisation de la classe."""
        self.total_species = 0
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
        species_data = self.process_folder(folder_path)
        
        if not species_data:
            QMessageBox.information(
                None, 
                "Information", 
                "Aucune donnée d'espèce trouvée dans les fichiers XML."
            )
            return
            
        # 3. Création de la couche temporaire
        temp_layer = self.create_temp_layer(species_data)
        
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
                "ZnieffXmlToLayerEsp: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
                "Biblizou", 
                level=Qgis.Warning
            )
        
        # 6. Résumé
        self.show_summary(len(species_data))
    
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
                "ZnieffXmlToLayerEsp: Aucun dossier spécifié", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        if not os.path.isdir(folder_path):
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Dossier introuvable: {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        try:
            # 1. Traitement des fichiers
            species_data = self.process_folder(folder_path)
            
            if not species_data:
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerEsp: Aucune espèce trouvée dans {folder_path}", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
                return False
                
            # 2. Création de la couche temporaire
            temp_layer = self.create_temp_layer(species_data)
            
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
                    "ZnieffXmlToLayerEsp: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
            
            # 5. Log du résumé
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Traitement terminé - "
                f"{self.processed_files} fichiers, {len(species_data)} espèces", 
                "Biblizou", 
                level=Qgis.Success
            )
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Erreur lors du traitement: {str(e)}", 
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
                "ZnieffXmlToLayerEsp: Annulation par l'utilisateur", 
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
        Retourne: liste de dictionnaires d'espèces
        """
        species_list = []
        
        # Filtrer les fichiers XML ZNIEFF (non FR, 13 caractères)
        xml_files = [
            f for f in os.listdir(folder_path) 
            if f.endswith('.xml') and not f.startswith('FR') and len(f) == 13
        ]
        
        if not xml_files:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Aucun fichier XML ZNIEFF trouvé dans {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return []
            
        QgsMessageLog.logMessage(
            f"ZnieffXmlToLayerEsp: {len(xml_files)} fichiers XML à traiter", 
            "Biblizou", 
            level=Qgis.Info
        )
        
        # Traiter chaque fichier
        for i, xml_file in enumerate(xml_files, 1):
            full_path = os.path.join(folder_path, xml_file)
            file_species = self.process_xml_file(full_path)
            
            if file_species:
                species_list.extend(file_species)
                self.processed_files += 1
                
            # Log de progression
            if i % 10 == 0 or i == len(xml_files):
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerEsp: Progression: {i}/{len(xml_files)} fichiers traités",
                    "Biblizou", 
                    level=Qgis.Info
                )
                
        self.total_species = len(species_list)
        return species_list
        
    def process_xml_file(self, xml_path):
        """Traite un fichier XML ZNIEFF individuel - Extraction complète de tous les champs."""
        species_data = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extraction infos générales ZNIEFF
            nm_sffzn = root.findtext('NM_SFFZN', '').strip()
            lb_zn = root.findtext('LB_ZN', '').strip()
            
            # Chercher toutes les espèces (ESPECE_PROJET_ROW et ESPECE_ROW)
            for species_row in root.iter():
                if species_row.tag in ['ESPECE_PROJET_ROW', 'ESPECE_ROW']:
                    # Extraction de TOUS les champs au niveau ESPECE_ROW
                    species_dict = {
                        'regne': species_row.findtext('REGNE', '').strip(),
                        'groupe': species_row.findtext('GROUPE', '').strip(),
                        'cd_nom': species_row.findtext('CD_NOM', '').strip(),
                        'fg_conf': species_row.findtext('FG_CONF', '').strip(),
                        'fg_esp': species_row.findtext('FG_ESP', '').strip(),
                        'nm_sffzn': species_row.findtext('NM_SFFZN', nm_sffzn).strip(),
                        'date_crea': species_row.findtext('DATE_CREA', '').strip(),
                        'date_modif': species_row.findtext('DATE_MODIF', '').strip(),
                        'nom_complet': species_row.findtext('NOM_COMPLET', '').strip(),
                        'nom_vern': species_row.findtext('NOM_VERN', '').strip(),
                        'origine': species_row.findtext('ORIGINE', '').strip(),
                        'lb_zn': lb_zn
                    }
                    species_data.append(species_dict)
                    
        except ET.ParseError as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Erreur de parsing XML {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Erreur traitement {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            
        return species_data
        
    def create_temp_layer(self, species_data):
        """Crée une couche temporaire QGIS sans géométrie avec les données d'espèces ZNIEFF."""
        # Définir tous les champs extraits du XML
        fields = [
            QgsField('regne', QVariant.String),
            QgsField('groupe', QVariant.String),
            QgsField('cd_nom', QVariant.String),
            QgsField('fg_conf', QVariant.String),
            QgsField('fg_esp', QVariant.String),
            QgsField('nm_sffzn', QVariant.String),
            QgsField('date_crea', QVariant.String),
            QgsField('date_modif', QVariant.String),
            QgsField('nom_complet', QVariant.String),
            QgsField('nom_vern', QVariant.String),
            QgsField('origine', QVariant.String),
            QgsField('lb_zn', QVariant.String)
        ]
        
        # Créer la couche (sans géométrie)
        layer = QgsVectorLayer("None", "Znieff_Especes_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        
        # Ajouter les features avec tous les champs
        features = []
        for data in species_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([
                data.get('regne', ''),
                data.get('groupe', ''),
                data.get('cd_nom', ''),
                data.get('fg_conf', ''),
                data.get('fg_esp', ''),
                data.get('nm_sffzn', ''),
                data.get('date_crea', ''),
                data.get('date_modif', ''),
                data.get('nom_complet', ''),
                data.get('nom_vern', ''),
                data.get('origine', ''),
                data.get('lb_zn', '')
            ])
            features.append(feat)
            
        provider.addFeatures(features)
        layer.updateExtents()
        
        QgsMessageLog.logMessage(
            f"ZnieffXmlToLayerEsp: Couche temporaire créée avec {len(species_data)} espèces et {len(fields)} champs", 
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
            save_options.layerName = "Znieff_Especes"
            
            if gpkg_exists:
                # Le fichier existe : on ajoute/remplace la couche
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerEsp: GeoPackage existant trouvé : {self.gpkg_path}", 
                    "Biblizou", 
                    level=Qgis.Info
                )
            else:
                # Le fichier n'existe pas : on le crée
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerEsp: Création d'un nouveau GeoPackage : {self.gpkg_path}", 
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
                    f"ZnieffXmlToLayerEsp: Couche sauvegardée avec succès dans {self.gpkg_path}", 
                    "Biblizou", 
                    level=Qgis.Success
                )
            else:
                self.gpkg_saved = False
                QgsMessageLog.logMessage(
                    f"ZnieffXmlToLayerEsp: Erreur lors de la sauvegarde : {error[1]}", 
                    "Biblizou", 
                    level=Qgis.Critical
                )
                
        except Exception as e:
            self.gpkg_saved = False
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Exception lors de la sauvegarde : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
    
    def load_from_geopackage(self):
        """Charge la couche depuis le GeoPackage dans QGIS."""
        try:
            # Construire l'URI pour charger la couche depuis le GeoPackage
            uri = f"{self.gpkg_path}|layername=Znieff_Especes"
            layer = QgsVectorLayer(uri, "Znieff_Especes", "ogr")
            
            if layer.isValid():
                # Supprimer l'ancienne couche si elle existe déjà dans le projet
                existing_layers = QgsProject.instance().mapLayersByName("Znieff_Especes")
                for existing_layer in existing_layers:
                    QgsProject.instance().removeMapLayer(existing_layer.id())
                
                # Ajouter la nouvelle couche
                QgsProject.instance().addMapLayer(layer)
                QgsMessageLog.logMessage(
                    "ZnieffXmlToLayerEsp: Couche chargée depuis le GeoPackage", 
                    "Biblizou", 
                    level=Qgis.Success
                )
            else:
                QgsMessageLog.logMessage(
                    "ZnieffXmlToLayerEsp: Erreur - la couche chargée n'est pas valide", 
                    "Biblizou", 
                    level=Qgis.Critical
                )
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZnieffXmlToLayerEsp: Erreur lors du chargement : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
        
    def show_summary(self, species_count):
        """Affiche un résumé du traitement (mode indépendant uniquement)."""
        gpkg_status = "✓ Sauvegardé avec succès" if self.gpkg_saved else "✗ Échec de sauvegarde (couche temporaire chargée)"
        
        summary = (
            f"Résultats du traitement ZNIEFF - Espèces:\n\n"
            f"• Fichiers XML traités: {self.processed_files}\n"
            f"• Espèces extraites: {species_count}\n"
            f"• Champs extraits: 12 champs complets\n\n"
            f"GeoPackage: {gpkg_status}\n"
            f"Chemin: {self.gpkg_path}\n\n"
            f"✓ Couche 'Znieff_Especes' chargée dans QGIS\n"
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
    module = ZnieffXmlToLayerEsp()
    module.run()


def run_module_with_path(folder_path):
    """
    Fonction d'exécution pour BiblizouMain.
    
    Args:
        folder_path (str): Chemin du dossier contenant les fichiers XML
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    module = ZnieffXmlToLayerEsp()
    return module.run_with_path(folder_path)


# Exécution
if __name__ == "__console__":
    # Mode console: exécuter en mode indépendant
    run_module()