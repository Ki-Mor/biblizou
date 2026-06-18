# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaXmlToLayerDesc.py
Groupe : FSD
Description : Module pour extraire les descriptions des sites Natura 2000 des fichiers XML
              et les exporter dans une couche QGIS enrichie sans géométrie.
"""

import os
import xml.etree.ElementTree as ET
import html
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

class NaturaXmlToLayerDesc:
    def __init__(self):
        """Initialisation de la classe."""
        self.processed_files = 0
        self.total_descriptions = 0
        self.gpkg_path = None
        self.gpkg_saved = False
        
    def run(self):
        """Point d'entrée principal du module (mode indépendant avec boîte de dialogue)."""
        # 1. Sélection du dossier via boîte de dialogue
        folder_path = self.select_folder_dialog()
        if not folder_path:
            return
            
        # 2. Traitement des fichiers
        descriptions_data = self.process_folder(folder_path)
        
        if not descriptions_data:
            QMessageBox.information(
                None, 
                "Information", 
                "Aucune description trouvée dans les fichiers XML."
            )
            return
            
        # 3. Création de la couche temporaire
        temp_layer = self.create_temp_layer(descriptions_data)
        if not temp_layer:
            QMessageBox.warning(None, "Erreur", "La couche n'a pas pu être créée correctement.")
            return
        # 4. Enregistrement dans GeoPackage
        self.gpkg_path = os.path.join(folder_path, "biblizou.gpkg")
        self.save_to_geopackage(temp_layer)
        # 5. Chargement depuis GeoPackage ou couche temporaire
        if self.gpkg_saved:
            self.load_from_geopackage()
        else:
            QgsProject.instance().addMapLayer(temp_layer)
            QgsMessageLog.logMessage(
                "NaturaXmlToLayerDesc: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)",
                "Biblizou",
                level=Qgis.Warning
            )
        # 6. Résumé
        self.show_summary(len(descriptions_data))
        
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
                "NaturaXmlToLayerDesc: Aucun dossier spécifié", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        if not os.path.isdir(folder_path):
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerDesc: Dossier introuvable: {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        try:
            # 1. Traitement des fichiers
            descriptions_data = self.process_folder(folder_path)
            
            if not descriptions_data:
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerDesc: Aucune description trouvée dans {folder_path}",
                    "Biblizou",
                    level=Qgis.Warning
                )
                return True

            # 2. Création de la couche temporaire
            temp_layer = self.create_temp_layer(descriptions_data)
            if not temp_layer:
                QgsMessageLog.logMessage(
                    "NaturaXmlToLayerDesc: Échec de création de la couche",
                    "Biblizou",
                    level=Qgis.Warning
                )
                return False
            # 3. Enregistrement dans GeoPackage
            self.gpkg_path = os.path.join(folder_path, "biblizou.gpkg")
            self.save_to_geopackage(temp_layer)
            # 4. Chargement depuis GeoPackage ou couche temporaire
            if self.gpkg_saved:
                self.load_from_geopackage()
            else:
                QgsProject.instance().addMapLayer(temp_layer)
                QgsMessageLog.logMessage(
                    "NaturaXmlToLayerDesc: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)",
                    "Biblizou",
                    level=Qgis.Warning
                )
            # 5. Log du résumé
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerDesc: Traitement terminé - "
                f"{self.processed_files} fichiers, {len(descriptions_data)} descriptions",
                "Biblizou",
                level=Qgis.Success
            )
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerDesc: Erreur lors du traitement: {str(e)}", 
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
        Retourne: liste de dictionnaires de descriptions
        """
        descriptions_data = []
        
        # Filtrer les fichiers FR*.xml (13 caractères)
        xml_files = [
            f for f in os.listdir(folder_path) 
            if f.startswith('FR') and f.endswith('.xml') and len(f) == 13
        ]
        
        if not xml_files:
            QgsMessageLog.logMessage(
                f"Aucun fichier XML Natura 2000 trouvé dans {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return []
            
        QgsMessageLog.logMessage(
            f"NaturaXmlToLayerDesc: {len(xml_files)} fichiers XML à traiter", 
            "Biblizou", 
            level=Qgis.Info
        )
        
        # Traiter chaque fichier
        for i, xml_file in enumerate(xml_files, 1):
            full_path = os.path.join(folder_path, xml_file)
            file_descriptions = self.process_xml_file(full_path)
            
            if file_descriptions:
                descriptions_data.extend(file_descriptions)
                self.processed_files += 1
                
            # Log de progression
            if i % 10 == 0 or i == len(xml_files):
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerDesc: Progression: {i}/{len(xml_files)} fichiers traités "
                    f"({len(file_descriptions)} descriptions)", 
                    "Biblizou", 
                    level=Qgis.Info
                )
                
        self.total_descriptions = len(descriptions_data)
        return descriptions_data
        
    def process_xml_file(self, xml_path):
        """Traite un fichier XML individuel."""
        descriptions_data = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extraire les informations du site
            sitecode_elem = root.find('SITECODE')
            site_name_elem = root.find('SITE_NAME')
            
            sitecode = sitecode_elem.text.strip() if sitecode_elem is not None and sitecode_elem.text else ""
            site_name = site_name_elem.text.strip() if site_name_elem is not None and site_name_elem.text else ""
            
            # Chercher les descriptions dans COMMENTAIRE
            commentaire_elem = root.find('COMMENTAIRE')
            
            if commentaire_elem is not None:
                for commentaire_row in commentaire_elem.findall('COMMENTAIRE_ROW'):
                    quality_elem = commentaire_row.find('QUALITY')
                    vulnar_elem = commentaire_row.find('VULNAR')
                    
                    quality = quality_elem.text.strip() if quality_elem is not None and quality_elem.text else ""
                    vulnar = vulnar_elem.text.strip() if vulnar_elem is not None and vulnar_elem.text else ""
                    
                    # Nettoyer les espaces multiples
                    quality = ' '.join(quality.split())
                    vulnar = ' '.join(vulnar.split())
                    
                    # Générer le HTML formaté pour le popup
                    html_popup = self.generate_html_popup(sitecode, site_name, quality, vulnar)
                    
                    # Préparer les données
                    description_data = {
                        'SITECODE': sitecode,
                        'SITE_NAME': site_name,
                        'QUALITY': quality,
                        'VULNAR': vulnar,
                        'HTML_POPUP': html_popup
                    }
                    
                    descriptions_data.append(description_data)
                        
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
            
        return descriptions_data
    
    def generate_html_popup(self, sitecode, site_name, quality, vulnar):
        """Génère le contenu HTML formaté pour le popup."""
        # Échapper les caractères HTML
        safe_sitecode = html.escape(sitecode)
        safe_site_name = html.escape(site_name)
        safe_quality = html.escape(quality).replace('\n', '<br>')
        safe_vulnar = html.escape(vulnar).replace('\n', '<br>')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 10px; }}
                .header {{ color: #009999; border-bottom: 2px solid #009999; padding-bottom: 5px; margin-bottom: 15px; }}
                .title {{ font-size: 16px; font-weight: bold; }}
                .subtitle {{ font-size: 14px; color: #666; }}
                .section {{ margin-bottom: 15px; }}
                .section-title {{ font-weight: bold; color: #009999; margin-bottom: 5px; }}
                .content {{ margin-left: 10px; text-align: justify; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">{safe_site_name}</div>
                <div class="subtitle">Code : {safe_sitecode}</div>
            </div>
            
            <div class="section">
                <div class="section-title">Valeur écologique (QUALITY) :</div>
                <div class="content">{safe_quality if safe_quality else '<i>Aucune information</i>'}</div>
            </div>
            
            <div class="section">
                <div class="section-title">Vulnérabilités (VULNAR) :</div>
                <div class="content">{safe_vulnar if safe_vulnar else '<i>Aucune information</i>'}</div>
            </div>
        </body>
        </html>
        """
        
        return html_content
        
    def create_temp_layer(self, descriptions_data):
        """Crée une couche temporaire QGIS sans géométrie avec les descriptions."""
        # Définir les champs
        fields = [
            QgsField('SITECODE', QVariant.String),
            QgsField('SITE_NAME', QVariant.String),
            QgsField('QUALITY', QVariant.String, len=10000),  # Texte long
            QgsField('VULNAR', QVariant.String, len=10000),   # Texte long
            QgsField('HTML_POPUP', QVariant.String, len=20000) # HTML formaté
        ]
        
        # Créer la couche temporaire (sans géométrie)
        layer = QgsVectorLayer("None", "Natura_2000_Descriptions_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        
        # Configurer le popup HTML
        layer.setDisplayExpression("SITE_NAME")
        
        # Ajouter les features
        features = []
        for data in descriptions_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([
                data.get('SITECODE', ''),
                data.get('SITE_NAME', ''),
                data.get('QUALITY', ''),
                data.get('VULNAR', ''),
                data.get('HTML_POPUP', '')
            ])
            features.append(feat)
            
        provider.addFeatures(features)
        layer.updateExtents()
        
        QgsMessageLog.logMessage(
            f"NaturaXmlToLayerDesc: Couche temporaire créée avec {len(descriptions_data)} entrées",
            "Biblizou",
            level=Qgis.Success
        )
        return layer

    def save_to_geopackage(self, layer):
        """Enregistre la couche dans un GeoPackage."""
        try:
            gpkg_exists = os.path.exists(self.gpkg_path)
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.driverName = "GPKG"
            save_options.layerName = "Natura_2000_Descriptions"
            if gpkg_exists:
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerDesc: GeoPackage existant trouvé : {self.gpkg_path}",
                    "Biblizou",
                    level=Qgis.Info
                )
            else:
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerDesc: Création d'un nouveau GeoPackage : {self.gpkg_path}",
                    "Biblizou",
                    level=Qgis.Info
                )
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                self.gpkg_path,
                QgsProject.instance().transformContext(),
                save_options
            )
            if error[0] == QgsVectorFileWriter.NoError:
                self.gpkg_saved = True
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerDesc: Couche sauvegardée avec succès dans {self.gpkg_path}",
                    "Biblizou",
                    level=Qgis.Success
                )
            else:
                self.gpkg_saved = False
                QgsMessageLog.logMessage(
                    f"NaturaXmlToLayerDesc: Erreur lors de la sauvegarde : {error[1]}",
                    "Biblizou",
                    level=Qgis.Critical
                )
        except Exception as e:
            self.gpkg_saved = False
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerDesc: Exception lors de la sauvegarde : {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )

    def load_from_geopackage(self):
        """Charge la couche depuis le GeoPackage dans QGIS."""
        try:
            uri = f"{self.gpkg_path}|layername=Natura_2000_Descriptions"
            layer = QgsVectorLayer(uri, "Natura_2000_Descriptions", "ogr")
            if layer.isValid():
                layer.setDisplayExpression("SITE_NAME")
                existing_layers = QgsProject.instance().mapLayersByName("Natura_2000_Descriptions")
                for existing_layer in existing_layers:
                    QgsProject.instance().removeMapLayer(existing_layer.id())
                QgsProject.instance().addMapLayer(layer)
                QgsMessageLog.logMessage(
                    "NaturaXmlToLayerDesc: Couche chargée depuis le GeoPackage",
                    "Biblizou",
                    level=Qgis.Success
                )
            else:
                QgsMessageLog.logMessage(
                    "NaturaXmlToLayerDesc: Erreur - la couche chargée n'est pas valide",
                    "Biblizou",
                    level=Qgis.Critical
                )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"NaturaXmlToLayerDesc: Erreur lors du chargement : {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )
        
    def show_summary(self, descriptions_count):
        """Affiche un résumé du traitement (mode indépendant uniquement)."""
        summary = (
            f"Résultats du traitement Natura 2000 - Descriptions:\n\n"
            f"• Fichiers XML traités: {self.processed_files}\n"
            f"• Descriptions extraites: {descriptions_count}\n\n"
            f"✓ Couche 'Natura 2000 - Descriptions' créée\n"
            f"✓ Contenu HTML généré pour les popups\n"
            f"✓ Les textes peuvent être copiés depuis la table attributaire"
        )
            
        QMessageBox.information(
            None,
            "Traitement terminé",
            summary
        )


# Pour exécuter le module dans QGIS
def run_module():
    """Fonction d'exécution pour QGIS (mode indépendant)."""
    module = NaturaXmlToLayerDesc()
    module.run()


def run_module_with_path(folder_path):
    """
    Fonction d'exécution pour BiblizouMain.
    
    Args:
        folder_path (str): Chemin du dossier contenant les fichiers XML
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    module = NaturaXmlToLayerDesc()
    return module.run_with_path(folder_path)


# Exécution
if __name__ == "__console__":
    # Mode console: exécuter en mode indépendant
    run_module()