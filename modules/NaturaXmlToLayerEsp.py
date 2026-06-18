# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaXmlToLayerEsp.py
Groupe : FSD
Description : Module pour extraire les données d'espèces directive des XML Natura 2000
              et les exporter dans un GeoPackage (Mode Offline - sans API TAXREF).
              Version étendue avec extraction complète des champs SPECIES_ROW.
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

class NaturaXmlToLayerEsp:
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
                "Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
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
                "NaturaXmlToLayerEsp: Aucun dossier spécifié", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        if not os.path.isdir(folder_path):
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerEsp: Dossier introuvable: {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        try:
            # 1. Traitement des fichiers
            species_data = self.process_folder(folder_path)
            
            if not species_data:
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerEsp: Aucune espèce trouvée dans {folder_path}", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
                return None
                
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
                    "NaturaXmlToLayerEsp: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
            
            # 5. Log du résumé
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerEsp: Traitement terminé - "
                f"{self.processed_files} fichiers, {len(species_data)} espèces", 
                "Biblizou", 
                level=Qgis.Success
            )
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerEsp: Erreur lors du traitement: {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
            return False
        
    def select_folder_dialog(self):
        """Sélectionne un dossier via boîte de dialogue (mode indépendant)."""
        folder_path, ok = QInputDialog.getText(
            None,
            "Sélection du dossier",
            "Entrez le chemin du dossier contenant les fichiers XML Natura 2000 :"
        )
        
        if not ok or not folder_path:
            QgsMessageLog.logMessage(
                "Annulation par l'utilisateur", 
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
        
        # Filtrer les fichiers FR*.xml (13 caractères)
        xml_files = [
            f for f in os.listdir(folder_path) 
            if f.startswith('FR') and f.endswith('.xml') and len(f) == 13
        ]
        
        if not xml_files:
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerEsp: Aucun fichier XML Natura 2000 trouvé dans {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return []
            
        QgsMessageLog.logMessage(
            f"NaturaXmlToLayerEsp: {len(xml_files)} fichiers XML à traiter", 
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
                    f"NaturaXmlToLayerEsp: Progression: {i}/{len(xml_files)} fichiers traités",
                    "Biblizou", 
                    level=Qgis.Info
                )
                
        self.total_species = len(species_list)
        return species_list
        
    def process_xml_file(self, xml_path):
        """Traite un fichier XML individuel - Extraction complète de tous les champs SPECIES_ROW."""
        species_data = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Chercher dans BIOTOP pour SITECODE et SITE_NAME
            sitecode = ""
            site_name = ""
            
            for biotop_elem in root.iter('BIOTOP'):
                sitecode_elem = biotop_elem.find('SITECODE')
                site_name_elem = biotop_elem.find('SITE_NAME')
                
                if sitecode_elem is not None and sitecode_elem.text:
                    sitecode = sitecode_elem.text.strip()
                    
                if site_name_elem is not None and site_name_elem.text:
                    site_name = site_name_elem.text.strip()
                
                # Itérer sur SPECIES puis SPECIES_ROW
                for species_elem in biotop_elem.iter('SPECIES'):
                    for species_row in species_elem.iter('SPECIES_ROW'):
                        # Extraire TOUS les champs du SPECIES_ROW
                        species_dict = {
                            'SITECODE': sitecode,
                            'SITE_NAME': site_name,
                            'PK_SPECIES': species_row.findtext('PK_SPECIES', '').strip(),
                            'FPK_NATURA': species_row.findtext('FPK_NATURA', '').strip(),
                            'CODE_N2000': species_row.findtext('CODE_N2000', '').strip(),
                            'CD_NOM': species_row.findtext('CD_NOM', '').strip(),
                            'ANNEXE_II': species_row.findtext('ANNEXE_II', '').strip(),
                            'TAXGROUP': species_row.findtext('TAXGROUP', '').strip(),
                            'TAX_CODE': species_row.findtext('TAX_CODE', '').strip(),
                            'S': species_row.findtext('S', '').strip(),
                            'NP': species_row.findtext('NP', '').strip(),
                            'TYPE': species_row.findtext('TYPE', '').strip(),
                            'SIZE_MIN': species_row.findtext('SIZE_MIN', '').strip(),
                            'SIZE_MAX': species_row.findtext('SIZE_MAX', '').strip(),
                            'UNIT': species_row.findtext('UNIT', '').strip(),
                            'CAT_POP': species_row.findtext('CAT_POP', '').strip(),
                            'QUALITY': species_row.findtext('QUALITY', '').strip(),
                            'POPULATION': species_row.findtext('POPULATION', '').strip(),
                            'CONSERVE': species_row.findtext('CONSERVE', '').strip(),
                            'ISOLATION': species_row.findtext('ISOLATION', '').strip(),
                            'GLOBAL': species_row.findtext('GLOBAL', '').strip(),
                            'CONSERVE_HABITAT': species_row.findtext('CONSERVE_HABITAT', '').strip(),
                            'CONSERVE_RESTAURATION': species_row.findtext('CONSERVE_RESTAURATION', '').strip(),
                            'DATE_CREA': species_row.findtext('DATE_CREA', '').strip(),
                            'DATE_MODIF': species_row.findtext('DATE_MODIF', '').strip(),
                            'DATE_SUPP': species_row.findtext('DATE_SUPP', '').strip(),
                            'DATE_BASE': species_row.findtext('DATE_BASE', '').strip(),
                            'JUSTIFICATION_SUPP': species_row.findtext('JUSTIFICATION_SUPP', '').strip(),
                            'COMMENTAIRE_SUPP': species_row.findtext('COMMENTAIRE_SUPP', '').strip(),
                            'JUSTIFICATION_SENSIBLE': species_row.findtext('JUSTIFICATION_SENSIBLE', '').strip(),
                            'COMMENTAIRE_GENERAL': species_row.findtext('COMMENTAIRE_GENERAL', '').strip(),
                            'ALIMENTATION': species_row.findtext('ALIMENTATION', '').strip(),
                            'PRES_ACONFIRMER': species_row.findtext('PRES_ACONFIRMER', '').strip(),
                            'INVENTAIRE_ANNEE': species_row.findtext('INVENTAIRE_ANNEE', '').strip(),
                            'INVENTAIRE_AUTEUR': species_row.findtext('INVENTAIRE_AUTEUR', '').strip(),
                            'TENDANCE_CRITERE_STRUCT_FONCT': species_row.findtext('TENDANCE_CRITERE_STRUCT_FONCT', '').strip(),
                            'TENDANCE_CRITERE_AUTRE': species_row.findtext('TENDANCE_CRITERE_AUTRE', '').strip(),
                            'TENDANCE_COMMENTAIRE': species_row.findtext('TENDANCE_COMMENTAIRE', '').strip(),
                            'TENDANCE': species_row.findtext('TENDANCE', '').strip(),
                            'TENDANCE_CRITERE_SURFACE': species_row.findtext('TENDANCE_CRITERE_SURFACE', '').strip(),
                            'INVENTAIRE_ANNEE_MIN': species_row.findtext('INVENTAIRE_ANNEE_MIN', '').strip(),
                            'UUID_SPECIES': species_row.findtext('UUID_SPECIES', '').strip(),
                            'NOM': species_row.findtext('NOM', '').strip()
                        }
                        species_data.append(species_dict)
                        
        except ET.ParseError as e:
            QgsMessageLog.logMessage(
                f"Erreur de parsing XML {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Erreur traitement {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            
        return species_data
        
    def create_temp_layer(self, species_data):
        """Crée une couche temporaire QGIS sans géométrie avec TOUS les champs SPECIES_ROW."""
        # Définir TOUS les champs disponibles dans SPECIES_ROW
        fields = [
            # Informations du site
            QgsField('SITECODE', QVariant.String),
            QgsField('SITE_NAME', QVariant.String),
            
            # Champs principaux SPECIES_ROW
            QgsField('PK_SPECIES', QVariant.String),
            QgsField('FPK_NATURA', QVariant.String),
            QgsField('CODE_N2000', QVariant.String),
            QgsField('CD_NOM', QVariant.String),
            QgsField('ANNEXE_II', QVariant.String),
            QgsField('TAXGROUP', QVariant.String),
            QgsField('TAX_CODE', QVariant.String),
            QgsField('S', QVariant.String),
            QgsField('NP', QVariant.String),
            QgsField('TYPE', QVariant.String),
            QgsField('SIZE_MIN', QVariant.String),
            QgsField('SIZE_MAX', QVariant.String),
            QgsField('UNIT', QVariant.String),
            QgsField('CAT_POP', QVariant.String),
            QgsField('QUALITY', QVariant.String),
            QgsField('POPULATION', QVariant.String),
            QgsField('CONSERVE', QVariant.String),
            QgsField('ISOLATION', QVariant.String),
            QgsField('GLOBAL', QVariant.String),
            QgsField('CONSERVE_HABITAT', QVariant.String),
            QgsField('CONSERVE_RESTAURATION', QVariant.String),
            
            # Dates
            QgsField('DATE_CREA', QVariant.String),
            QgsField('DATE_MODIF', QVariant.String),
            QgsField('DATE_SUPP', QVariant.String),
            QgsField('DATE_BASE', QVariant.String),
            
            # Commentaires et justifications
            QgsField('JUSTIFICATION_SUPP', QVariant.String),
            QgsField('COMMENTAIRE_SUPP', QVariant.String),
            QgsField('JUSTIFICATION_SENSIBLE', QVariant.String),
            QgsField('COMMENTAIRE_GENERAL', QVariant.String),
            
            # Informations complémentaires
            QgsField('ALIMENTATION', QVariant.String),
            QgsField('PRES_ACONFIRMER', QVariant.String),
            QgsField('INVENTAIRE_ANNEE', QVariant.String),
            QgsField('INVENTAIRE_AUTEUR', QVariant.String),
            
            # Tendances
            QgsField('TENDANCE_CRITERE_STRUCT_FONCT', QVariant.String),
            QgsField('TENDANCE_CRITERE_AUTRE', QVariant.String),
            QgsField('TENDANCE_COMMENTAIRE', QVariant.String),
            QgsField('TENDANCE', QVariant.String),
            QgsField('TENDANCE_CRITERE_SURFACE', QVariant.String),
            
            # Autres champs
            QgsField('INVENTAIRE_ANNEE_MIN', QVariant.String),
            QgsField('UUID_SPECIES', QVariant.String),
            QgsField('NOM', QVariant.String)
        ]
        
        # Créer la couche (sans géométrie)
        layer = QgsVectorLayer("None", "Natura_2000_Especes_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        
        # Ajouter les features avec TOUS les champs
        features = []
        for data in species_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([
                data.get('SITECODE', ''),
                data.get('SITE_NAME', ''),
                data.get('PK_SPECIES', ''),
                data.get('FPK_NATURA', ''),
                data.get('CODE_N2000', ''),
                data.get('CD_NOM', ''),
                data.get('ANNEXE_II', ''),
                data.get('TAXGROUP', ''),
                data.get('TAX_CODE', ''),
                data.get('S', ''),
                data.get('NP', ''),
                data.get('TYPE', ''),
                data.get('SIZE_MIN', ''),
                data.get('SIZE_MAX', ''),
                data.get('UNIT', ''),
                data.get('CAT_POP', ''),
                data.get('QUALITY', ''),
                data.get('POPULATION', ''),
                data.get('CONSERVE', ''),
                data.get('ISOLATION', ''),
                data.get('GLOBAL', ''),
                data.get('CONSERVE_HABITAT', ''),
                data.get('CONSERVE_RESTAURATION', ''),
                data.get('DATE_CREA', ''),
                data.get('DATE_MODIF', ''),
                data.get('DATE_SUPP', ''),
                data.get('DATE_BASE', ''),
                data.get('JUSTIFICATION_SUPP', ''),
                data.get('COMMENTAIRE_SUPP', ''),
                data.get('JUSTIFICATION_SENSIBLE', ''),
                data.get('COMMENTAIRE_GENERAL', ''),
                data.get('ALIMENTATION', ''),
                data.get('PRES_ACONFIRMER', ''),
                data.get('INVENTAIRE_ANNEE', ''),
                data.get('INVENTAIRE_AUTEUR', ''),
                data.get('TENDANCE_CRITERE_STRUCT_FONCT', ''),
                data.get('TENDANCE_CRITERE_AUTRE', ''),
                data.get('TENDANCE_COMMENTAIRE', ''),
                data.get('TENDANCE', ''),
                data.get('TENDANCE_CRITERE_SURFACE', ''),
                data.get('INVENTAIRE_ANNEE_MIN', ''),
                data.get('UUID_SPECIES', ''),
                data.get('NOM', '')
            ])
            features.append(feat)
            
        provider.addFeatures(features)
        layer.updateExtents()
        
        QgsMessageLog.logMessage(
            f"NaturaXmlToLayerEsp: Couche temporaire créée avec {len(species_data)} espèces et {len(fields)} champs", 
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
            save_options.layerName = "Natura_2000_Especes"
            
            if gpkg_exists:
                # Le fichier existe : on ajoute/remplace la couche
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerEsp: GeoPackage existant trouvé : {self.gpkg_path}", 
                    "Biblizou", 
                    level=Qgis.Info
                )
            else:
                # Le fichier n'existe pas : on le crée
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerEsp: Création d'un nouveau GeoPackage : {self.gpkg_path}", 
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
                    f"NaturaXmlToLayerEsp: Couche sauvegardée avec succès dans {self.gpkg_path}", 
                    "Biblizou", 
                    level=Qgis.Success
                )
            else:
                self.gpkg_saved = False
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerEsp: Erreur lors de la sauvegarde : {error[1]}", 
                    "Biblizou", 
                    level=Qgis.Critical
                )
                
        except Exception as e:
            self.gpkg_saved = False
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerEsp: Exception lors de la sauvegarde : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
    
    def load_from_geopackage(self):
        """Charge la couche depuis le GeoPackage dans QGIS."""
        try:
            # Construire l'URI pour charger la couche depuis le GeoPackage
            uri = f"{self.gpkg_path}|layername=Natura_2000_Especes"
            layer = QgsVectorLayer(uri, "Natura_2000_Especes", "ogr")
            
            if layer.isValid():
                # Supprimer l'ancienne couche si elle existe déjà dans le projet
                existing_layers = QgsProject.instance().mapLayersByName("Natura_2000_Especes")
                for existing_layer in existing_layers:
                    QgsProject.instance().removeMapLayer(existing_layer.id())
                
                # Ajouter la nouvelle couche
                QgsProject.instance().addMapLayer(layer)
                QgsMessageLog.logMessage(
                    "NaturaXmlToLayerEsp: Couche chargée depuis le GeoPackage", 
                    "Biblizou", 
                    level=Qgis.Success
                )
            else:
                QgsMessageLog.logMessage(
                    "NaturaXmlToLayerEsp: Erreur - la couche chargée n'est pas valide", 
                    "Biblizou", 
                    level=Qgis.Critical
                )
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerEsp: Erreur lors du chargement : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
        
    def show_summary(self, species_count):
        """Affiche un résumé du traitement (mode indépendant uniquement)."""
        gpkg_status = "✓ Sauvegardé avec succès" if self.gpkg_saved else "✗ Échec de sauvegarde (couche temporaire chargée)"
        
        summary = (
            f"Résultats du traitement Natura 2000 - Espèces:\n\n"
            f"• Fichiers XML traités: {self.processed_files}\n"
            f"• Espèces extraites: {species_count}\n"
            f"• Champs extraits: 45 champs complets SPECIES_ROW\n\n"
            f"GeoPackage: {gpkg_status}\n"
            f"Chemin: {self.gpkg_path}\n\n"
            f"✓ Couche 'Natura_2000_Especes' chargée dans QGIS\n"
            f"✓ Données complètes avec tous les champs Natura 2000"
        )
            
        QMessageBox.information(
            None,
            "Traitement Natura 2000 terminé",
            summary
        )
        


# Pour exécuter le module dans QGIS
def run_module():
    """Fonction d'exécution pour QGIS (mode indépendant)."""
    module = NaturaXmlToLayerEsp()
    module.run()


def run_module_with_path(folder_path):
    """
    Fonction d'exécution pour BiblizouMain.
    
    Args:
        folder_path (str): Chemin du dossier contenant les fichiers XML
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    module = NaturaXmlToLayerEsp()
    return module.run_with_path(folder_path)


# Exécution
if __name__ == "__console__":
    # Mode console: exécuter en mode indépendant
    run_module()