"""
Auteur : ExEco Environnement - François Botcazou
Date : 2025/03
Version : 1.7
Nom : ZnieffXmlToLayerDesc.py
Groupe : Biblizou_PatNat
Description : Module pour extraire les descriptions des sites ZNIEFF des fichiers XML
              et les exporter dans une couche QGIS enrichie sans géométrie.
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
import traceback


class ZnieffXmlToLayerDesc:
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
                "Aucune description trouvée dans les fichiers XML ZNIEFF.\n\n"
                "Assurez-vous que les fichiers XML contiennent bien des données ZNIEFF "
                "et qu'ils suivent le format attendu."
            )
            return
            
        # 3. Création de la couche temporaire
        temp_layer = self.create_temp_layer(descriptions_data)
        
        if temp_layer:
            # 4. Enregistrement dans GeoPackage
            self.gpkg_path = os.path.join(folder_path, "biblizou.gpkg")
            self.save_to_geopackage(temp_layer)
            # 5. Chargement depuis GeoPackage ou couche temporaire
            if self.gpkg_saved:
                self.load_from_geopackage()
            else:
                QgsProject.instance().addMapLayer(temp_layer)
                QgsMessageLog.logMessage(
                    "[ZnieffXmlToLayerDesc]: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)",
                    "Biblizou",
                    level=Qgis.Warning
                )
            # 6. Résumé
            self.show_summary(len(descriptions_data), temp_layer.featureCount())
        else:
            QMessageBox.warning(
                None,
                "Erreur",
                "La couche n'a pas pu être créée correctement."
            )
        
    def run_with_path(self, folder_path):
        """
        Point d'entrée pour BiblizouMain (sans boîte de dialogue).
        
        Args:
            folder_path (str): Chemin du dossier contenant les fichiers XML ZNIEFF
            
        Returns:
            bool: True si le traitement a réussi, False sinon
        """
        if not folder_path:
            QgsMessageLog.logMessage(
                "[ZnieffXmlToLayerDesc]: Aucun dossier spécifié", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        if not os.path.isdir(folder_path):
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: Dossier introuvable: {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return False
            
        try:
            # 1. Traitement des fichiers
            descriptions_data = self.process_folder(folder_path)
            
            if not descriptions_data:
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: Aucune description trouvée dans {folder_path}", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
                return True  # Retourne True même si pas de données
            
            # 2. Création de la couche temporaire
            temp_layer = self.create_temp_layer(descriptions_data)
            
            if not temp_layer:
                QgsMessageLog.logMessage(
                    "[ZnieffXmlToLayerDesc]: Échec de création de la couche",
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
                    "[ZnieffXmlToLayerDesc]: Couche temporaire ajoutée (échec de sauvegarde GeoPackage)",
                    "Biblizou",
                    level=Qgis.Warning
                )
            
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: Traitement terminé - "
                f"{self.processed_files} fichiers, {temp_layer.featureCount()} descriptions",
                "Biblizou",
                level=Qgis.Success
            )
            return True
                
        except Exception as e:
            error_msg = f"[ZnieffXmlToLayerDesc]: Erreur lors du traitement: {str(e)}"
            QgsMessageLog.logMessage(error_msg, "Biblizou", level=Qgis.Critical)
            QgsMessageLog.logMessage(traceback.format_exc(), "Biblizou", level=Qgis.Critical)
            return False
        
    def select_folder_dialog(self):
        """Sélectionne un dossier via boîte de dialogue (mode indépendant)."""
        folder_path = QInputDialog.getText(
            None,
            "Sélection du dossier ZNIEFF",
            "Entrez le chemin du dossier contenant les fichiers XML ZNIEFF :"
        )[0]
        
        if not folder_path:
            QgsMessageLog.logMessage(
                "[ZnieffXmlToLayerDesc]: Annulation par l'utilisateur", 
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
        Traite tous les fichiers XML ZNIEFF du dossier.
        Retourne: liste de dictionnaires de descriptions
        """
        descriptions_data = []
        
        # Filtrer les fichiers ZNIEFF - version plus permissive
        xml_files = [
            f for f in os.listdir(folder_path) 
            if f.endswith('.xml')  # Accepter tous les fichiers XML
        ]
        
        if not xml_files:
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: Aucun fichier XML trouvé dans {folder_path}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            return []
            
        QgsMessageLog.logMessage(
            f"[ZnieffXmlToLayerDesc]: {len(xml_files)} fichiers XML à traiter dans {folder_path}", 
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
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: Fichier {xml_file} : {len(file_descriptions)} descriptions extraites", 
                    "Biblizou", 
                    level=Qgis.Info
                )
                
            # Log de progression
            if i % 10 == 0 or i == len(xml_files):
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: Progression: {i}/{len(xml_files)} fichiers traités "
                    f"({len(descriptions_data)} descriptions au total)", 
                    "Biblizou", 
                    level=Qgis.Info
                )
                
        self.total_descriptions = len(descriptions_data)
        
        if not descriptions_data:
            QgsMessageLog.logMessage(
                "[ZnieffXmlToLayerDesc]: Aucune description extraite des fichiers XML", 
                "Biblizou", 
                level=Qgis.Warning
            )
            
        return descriptions_data
    
    def extract_text_content(self, element):
        """
        Fonction générique pour extraire le contenu texte d'un élément XML.
        Gère différents formats de contenu.
        """
        if element is None:
            return ""
        
        # Méthode 1: Texte direct
        if element.text and element.text.strip():
            text = element.text.strip()
        else:
            # Méthode 2: Chercher les paragraphes <p>
            paragraphs = []
            for p_elem in element.findall('.//p'):
                if p_elem.text:
                    paragraphs.append(p_elem.text.strip())
            
            if paragraphs:
                text = '\n'.join(paragraphs)
            else:
                # Méthode 3: Extraire tout le texte de l'élément
                text = ''.join(element.itertext()).strip()
        
        # Nettoyer les espaces multiples
        if text:
            text = ' '.join(text.split())
        
        return text
        
    def process_xml_file(self, xml_path):
        """Traite un fichier XML ZNIEFF individuel."""
        descriptions_data = []
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Chercher tous les éléments ZNIEFF
            znieff_elements = list(root.iter('ZNIEFF'))
            
            for znieff_elem in znieff_elements:
                # Extraire le numéro ZNIEFF pour le débogage
                nm_sffzn_elem = znieff_elem.find('NM_SFFZN')
                nm_sffzn = self.get_element_text(nm_sffzn_elem)
                
                # Extraire les informations de base
                volet_znieff_elem = znieff_elem.find('VOLET_ZNIEFF')
                territoire_element = znieff_elem.find('TERRITOIRE')
                nm_sffzn_parent_elem = znieff_elem.find('NM_SFFZN_PARENT')
                nm_reg = znieff_elem.find('NM_REGZN')
                lb_zn_elem = znieff_elem.find('LB_ZN')
                ty_zone_elem = znieff_elem.find('TY_ZONE')
                su_zn_elem = znieff_elem.find('SU_ZN')
                prof_mini_elem = znieff_elem.find('PROF_MINI')
                prof_maxi_elem = znieff_elem.find('PROF_MAXI')
                alt_mini_elem = znieff_elem.find('ALT_MINI')
                alt_maxi_elem = znieff_elem.find('ALT_MAXI')
                x_l2e_elem = znieff_elem.find('X_L2E')
                y_l2e_elem = znieff_elem.find('Y_L2E')
                fg_evol_elem = znieff_elem.find('FG_EVOL')
                fg_evol_anc_elem = znieff_elem.find('FG_EVOL_ANC')
                fg_contour_elem = znieff_elem.find('FG_CONTOUR')
                tx_geo_elem = znieff_elem.find('TX_GEO')
                tx_acth_elem = znieff_elem.find('TX_ACTH')
                tx_mespro_elem = znieff_elem.find('TX_MESPRO')
                tx_hydro_elem = znieff_elem.find('TX_HYDRO')
                tx_granulo_elem = znieff_elem.find('TX_GRANULO')
                tx_interet_elem = znieff_elem.find('TX_INTERET')
                tx_fact_elem = znieff_elem.find('TX_FACT')
                tx_gene_elem = znieff_elem.find('TX_GENE')
                tx_delim_elem = znieff_elem.find('TX_DELIM')
                tx_typo_elem = znieff_elem.find('TX_TYPO')
                fg_sup_elem = znieff_elem.find('FG_SUPP')
                date_crea_elem = znieff_elem.find('DATE_CREA')
                date_modif_elem = znieff_elem.find('DATE_MODIF')
                type1_inclu_elem = znieff_elem.find('TYPE1_INCLU')
                inclu_dans_type2_elem = znieff_elem.find('INCLU_DANS_TYPE2')
                
                # Extraire les informations ZNI (imbriquées)
                zni_data = self.extract_zni_data(znieff_elem)
                
                # Récupérer les valeurs avec des valeurs par défaut vides
                volet_znieff = self.get_element_text(volet_znieff_elem)
                territoire = self.get_element_text(territoire_element)
                nm_sffzn_parent = self.get_element_text(nm_sffzn_parent_elem)
                nm_regzn = self.get_element_text(nm_reg)
                lb_zn = self.get_element_text(lb_zn_elem)
                ty_zone = self.get_element_text(ty_zone_elem)
                su_zn = self.get_element_text(su_zn_elem)
                prof_mini = self.get_element_text(prof_mini_elem)
                prof_maxi = self.get_element_text(prof_maxi_elem)
                alt_mini = self.get_element_text(alt_mini_elem)
                alt_maxi = self.get_element_text(alt_maxi_elem)
                x_l2e = self.get_element_text(x_l2e_elem)
                y_l2e = self.get_element_text(y_l2e_elem)
                fg_evol = self.get_element_text(fg_evol_elem)
                fg_evol_anc = self.get_element_text(fg_evol_anc_elem)
                fg_contour = self.get_element_text(fg_contour_elem)
                
                # Utiliser la fonction d'extraction pour les champs texte
                tx_geo = self.extract_text_content(tx_geo_elem)
                tx_acth = self.extract_text_content(tx_acth_elem)
                tx_mespro = self.extract_text_content(tx_mespro_elem)
                tx_hydro = self.extract_text_content(tx_hydro_elem)
                tx_granulo = self.extract_text_content(tx_granulo_elem)
                tx_interet = self.extract_text_content(tx_interet_elem)
                tx_fact = self.extract_text_content(tx_fact_elem)
                description_text = self.extract_text_content(tx_gene_elem)
                tx_delim = self.extract_text_content(tx_delim_elem)
                tx_typo = self.extract_text_content(tx_typo_elem)
                
                fg_supp = self.get_element_text(fg_sup_elem)
                date_crea = self.get_element_text(date_crea_elem)
                date_modif = self.get_element_text(date_modif_elem)
                type1_inclu = self.get_element_text(type1_inclu_elem)
                inclu_dans_type2 = self.get_element_text(inclu_dans_type2_elem)
                
                # Vérifier si nous avons des données valides
                if nm_sffzn or lb_zn or description_text:
                    # Générer le HTML formaté pour le popup
                    html_popup = self.generate_html_popup(nm_sffzn, lb_zn, description_text)
                    
                    # Préparer les données avec tous les champs
                    description_data = {
                        'NM_SFFZN': nm_sffzn,                # Numéro ZNIEFF
                        'VOLET_ZNIEFF': volet_znieff,        # Volet ZNIEFF
                        'TERRITOIRE': territoire,            # Territoire
                        'NM_SFFZN_PARENT': nm_sffzn_parent,  # Numéro ZNIEFF parent
                        'NM_REGZN': nm_regzn,                # Numéro région
                        'LB_ZN': lb_zn,                      # Nom du site
                        'TY_ZONE': ty_zone,                  # Type de zone
                        'SU_ZN': su_zn,                      # Surface
                        'PROF_MINI': prof_mini,              # Profondeur minimum
                        'PROF_MAXI': prof_maxi,              # Profondeur maximum
                        'ALT_MINI': alt_mini,                # Altitude minimum
                        'ALT_MAXI': alt_maxi,                # Altitude maximum
                        'X_L2E': x_l2e,                      # Coordonnée X
                        'Y_L2E': y_l2e,                      # Coordonnée Y
                        'FG_EVOL': fg_evol,                  # Évolution
                        'FG_EVOL_ANC': fg_evol_anc,          # Évolution antérieure
                        'FG_CONTOUR': fg_contour,            # Contour
                        'TX_GEO': tx_geo,                    # Géologie
                        'TX_ACTH': tx_acth,                  # Activités humaines
                        'TX_MESPRO': tx_mespro,              # Mesures de protection
                        'TX_HYDRO': tx_hydro,                # Hydrologie
                        'TX_GRANULO': tx_granulo,            # Granulométrie
                        'TX_INTERET': tx_interet,            # Intérêt
                        'TX_FACT': tx_fact,                  # Facteurs
                        'DESCRIPTION': description_text,     # Description complète
                        'TX_DELIM': tx_delim,                # Délimitation
                        'TX_TYPO': tx_typo,                  # Typologie
                        'FG_SUPP': fg_supp,                  # Suppression
                        'DATE_CREA': date_crea,              # Date création
                        'DATE_MODIF': date_modif,            # Date modification
                        'TYPE1_INCLU': type1_inclu,          # Type 1 inclus
                        'INCLU_DANS_TYPE2': inclu_dans_type2, # Inclus dans type 2
                        'HTML_POPUP': html_popup,            # HTML formaté
                        
                        # Champs ZNI
                        'ZNI_ID_ZNIEFF': zni_data.get('ID_ZNIEFF', ''),
                        'ZNI_NM_SFFZN': zni_data.get('NM_SFFZN', ''),
                        'ZNI_LB_ZN': zni_data.get('LB_ZN', ''),
                        'ZNI_TY_ZONE': zni_data.get('TY_ZONE', ''),
                        'ZNI_NM_REGZN': zni_data.get('NM_REGZN', ''),
                        'ZNI_VOLET_ZNIEFF': zni_data.get('VOLET_ZNIEFF', '')
                    }
                    
                    descriptions_data.append(description_data)
                    
                    QgsMessageLog.logMessage(
                        f"[ZnieffXmlToLayerDesc]: ✓ Description extraite: {lb_zn} ({nm_sffzn})", 
                        "Biblizou", 
                        level=Qgis.Info
                    )
                        
        except ET.ParseError as e:
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: Erreur de parsing XML {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: Erreur traitement {os.path.basename(xml_path)}: {str(e)}", 
                "Biblizou", 
                level=Qgis.Warning
            )
            
        return descriptions_data
    
    def get_element_text(self, element):
        """Récupère le texte d'un élément XML simple."""
        if element is not None and element.text:
            return element.text.strip()
        return ""
    
    def extract_zni_data(self, znieff_elem):
        """Extrait les données ZNI imbriquées."""
        zni_data = {}
        
        # Chercher l'élément ZNI
        zni_elem = znieff_elem.find('ZNI')
        if zni_elem is not None:
            # Chercher ZNI_ROW
            zni_row_elem = zni_elem.find('ZNI_ROW')
            if zni_row_elem is not None:
                # Extraire les champs ZNI
                zni_data['ID_ZNIEFF'] = self.get_element_text(zni_row_elem.find('ID_ZNIEFF'))
                zni_data['NM_SFFZN'] = self.get_element_text(zni_row_elem.find('NM_SFFZN'))
                zni_data['LB_ZN'] = self.get_element_text(zni_row_elem.find('LB_ZN'))
                zni_data['TY_ZONE'] = self.get_element_text(zni_row_elem.find('TY_ZONE'))
                zni_data['NM_REGZN'] = self.get_element_text(zni_row_elem.find('NM_REGZN'))
                zni_data['VOLET_ZNIEFF'] = self.get_element_text(zni_row_elem.find('VOLET_ZNIEFF'))
        
        return zni_data
    
    def generate_html_popup(self, nm_sffzn, lb_zn, description):
        """Génère le contenu HTML formaté pour le popup ZNIEFF."""
        # Échapper les caractères HTML
        safe_nm_sffzn = html.escape(nm_sffzn) if nm_sffzn else "Non renseigné"
        safe_lb_zn = html.escape(lb_zn) if lb_zn else "Non renseigné"
        
        # Traiter la description
        if description:
            # Échaper d'abord, puis remplacer les retours à la ligne
            safe_description = html.escape(description)
            # Remplacer les doubles espaces
            safe_description = safe_description.replace('  ', ' ')
            # Convertir les retours à la ligne en <br>
            safe_description = safe_description.replace('\n', '<br>')
        else:
            safe_description = '<i>Aucune description disponible</i>'
        
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
                .content {{ margin-left: 10px; text-align: justify; line-height: 1.5; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">{safe_lb_zn}</div>
                <div class="subtitle">ZNIEFF : {safe_nm_sffzn}</div>
            </div>
            
            <div class="section">
                <div class="section-title">Description :</div>
                <div class="content">{safe_description}</div>
            </div>
        </body>
        </html>
        """
        
        return html_content        

    def create_temp_layer(self, descriptions_data):
        """Crée une couche temporaire QGIS sans géométrie avec les descriptions ZNIEFF."""
        QgsMessageLog.logMessage(
            f"[ZnieffXmlToLayerDesc]: Début création couche temporaire avec {len(descriptions_data)} descriptions",
            "Biblizou",
            level=Qgis.Info
        )
        
        # Définir les champs SANS limite de longueur (comme vous l'avez fait)
        fields = [
            QgsField('NM_SFFZN', QVariant.String),               # Numéro ZNIEFF - texte
            QgsField('VOLET_ZNIEFF', QVariant.String),           # Volet ZNIEFF - texte
            QgsField('TERRITOIRE', QVariant.String),             # Territoire - texte
            QgsField('NM_SFFZN_PARENT', QVariant.String),        # Numéro ZNIEFF parent - texte
            QgsField('NM_REGZN', QVariant.String),               # Numéro région - texte
            QgsField('LB_ZN', QVariant.String),                  # Nom du site - texte
            QgsField('TY_ZONE', QVariant.String),                # Type de zone - texte
            QgsField('SU_ZN', QVariant.Double),                  # Surface - réel
            QgsField('PROF_MINI', QVariant.Double),              # Profondeur minimum - réel
            QgsField('PROF_MAXI', QVariant.Double),              # Profondeur maximum - réel
            QgsField('ALT_MINI', QVariant.Double),               # Altitude minimum - réel
            QgsField('ALT_MAXI', QVariant.Double),               # Altitude maximum - réel
            QgsField('X_L2E', QVariant.Double),                  # Coordonnée X - réel
            QgsField('Y_L2E', QVariant.Double),                  # Coordonnée Y - réel
            QgsField('FG_EVOL', QVariant.String),                # Évolution - texte
            QgsField('FG_EVOL_ANC', QVariant.String),            # Évolution antérieure - texte
            QgsField('FG_CONTOUR', QVariant.String),             # Contour - texte
            QgsField('TX_GEO', QVariant.String),                 # Géologie - texte
            QgsField('TX_ACTH', QVariant.String),                # Activités humaines - texte
            QgsField('TX_MESPRO', QVariant.String),              # Mesures de protection - texte
            QgsField('TX_HYDRO', QVariant.String),               # Hydrologie - texte
            QgsField('TX_GRANULO', QVariant.String),             # Granulométrie - texte
            QgsField('TX_INTERET', QVariant.String),             # Intérêt - texte
            QgsField('TX_FACT', QVariant.String),                # Facteurs - texte
            QgsField('DESCRIPTION', QVariant.String),            # Description complète - texte
            QgsField('TX_DELIM', QVariant.String),               # Délimitation - texte
            QgsField('TX_TYPO', QVariant.String),                # Typologie - texte
            QgsField('FG_SUPP', QVariant.String),                # Suppression - texte
            QgsField('DATE_CREA', QVariant.String),              # Date création - date (texte)
            QgsField('DATE_MODIF', QVariant.String),             # Date modification - date (texte)
            QgsField('TYPE1_INCLU', QVariant.String),            # Type 1 inclus - texte
            QgsField('INCLU_DANS_TYPE2', QVariant.String),       # Inclus dans type 2 - texte
            QgsField('ZNI_ID_ZNIEFF', QVariant.String),          # ZNI ID ZNIEFF - texte
            QgsField('ZNI_NM_SFFZN', QVariant.String),           # ZNI Numéro ZNIEFF - texte
            QgsField('ZNI_LB_ZN', QVariant.String),              # ZNI Nom du site - texte
            QgsField('ZNI_TY_ZONE', QVariant.String),            # ZNI Type de zone - texte
            QgsField('ZNI_NM_REGZN', QVariant.String),           # ZNI Numéro région - texte
            QgsField('ZNI_VOLET_ZNIEFF', QVariant.String),       # ZNI Volet ZNIEFF - texte
            QgsField('HTML_POPUP', QVariant.String)              # HTML formaté - texte
        ]
        
        # Créer la couche temporaire (sans géométrie)
        layer = QgsVectorLayer("None", "Znieff_Descriptions_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        
        QgsMessageLog.logMessage(
            f"[ZnieffXmlToLayerDesc]: Nouvelle couche créée avec {len(fields)} champs", 
            "Biblizou", 
            level=Qgis.Info
        )
        
        # Configurer l'expression d'affichage
        layer.setDisplayExpression("coalesce(LB_ZN, '') || ' (' || coalesce(NM_SFFZN, '') || ')'")
        
        # Ajouter les features UNE PAR UNE pour mieux déboguer les erreurs
        success_count = 0
        error_count = 0
        error_details = []
        
        for i, data in enumerate(descriptions_data, 1):
            try:
                feat = QgsFeature()
                feat.setFields(layer.fields())
                
                # Convertir les valeurs numériques
                su_zn = self.convert_to_double(data.get('SU_ZN', ''))
                prof_mini = self.convert_to_double(data.get('PROF_MINI', ''))
                prof_maxi = self.convert_to_double(data.get('PROF_MAXI', ''))
                alt_mini = self.convert_to_double(data.get('ALT_MINI', ''))
                alt_maxi = self.convert_to_double(data.get('ALT_MAXI', ''))
                x_l2e = self.convert_to_double(data.get('X_L2E', ''))
                y_l2e = self.convert_to_double(data.get('Y_L2E', ''))
                
                # Créer la liste d'attributs - PAS DE TRONCATURE AUTOMATIQUE
                # Les champs sont maintenant illimités
                feat.setAttributes([
                    data.get('NM_SFFZN', ''),
                    data.get('VOLET_ZNIEFF', ''),
                    data.get('TERRITOIRE', ''),
                    data.get('NM_SFFZN_PARENT', ''),
                    data.get('NM_REGZN', ''),
                    data.get('LB_ZN', ''),
                    data.get('TY_ZONE', ''),
                    su_zn,
                    prof_mini,
                    prof_maxi,
                    alt_mini,
                    alt_maxi,
                    x_l2e,
                    y_l2e,
                    data.get('FG_EVOL', ''),
                    data.get('FG_EVOL_ANC', ''),
                    data.get('FG_CONTOUR', ''),
                    data.get('TX_GEO', ''),
                    data.get('TX_ACTH', ''),
                    data.get('TX_MESPRO', ''),
                    data.get('TX_HYDRO', ''),
                    data.get('TX_GRANULO', ''),
                    data.get('TX_INTERET', ''),
                    data.get('TX_FACT', ''),
                    data.get('DESCRIPTION', ''),  # Peut être très long
                    data.get('TX_DELIM', ''),
                    data.get('TX_TYPO', ''),
                    data.get('FG_SUPP', ''),
                    data.get('DATE_CREA', ''),
                    data.get('DATE_MODIF', ''),
                    data.get('TYPE1_INCLU', ''),
                    data.get('INCLU_DANS_TYPE2', ''),
                    data.get('ZNI_ID_ZNIEFF', ''),
                    data.get('ZNI_NM_SFFZN', ''),
                    data.get('ZNI_LB_ZN', ''),
                    data.get('ZNI_TY_ZONE', ''),
                    data.get('ZNI_NM_REGZN', ''),
                    data.get('ZNI_VOLET_ZNIEFF', ''),
                    data.get('HTML_POPUP', '')    # Peut être très long (HTML)
                ])
                
                # Ajouter la feature
                if provider.addFeature(feat):
                    success_count += 1
                    if i % 10 == 0:
                        QgsMessageLog.logMessage(
                            f"[ZnieffXmlToLayerDesc]: ✓ {i} features ajoutées", 
                            "Biblizou", 
                            level=Qgis.Info
                        )
                else:
                    error_count += 1
                    error_details.append(f"Feature {i}: Échec d'ajout")
                    QgsMessageLog.logMessage(
                        f"[ZnieffXmlToLayerDesc]: ✗ Erreur ajout feature {i}", 
                        "Biblizou", 
                        level=Qgis.Warning
                    )
                    
            except Exception as e:
                error_count += 1
                error_details.append(f"Feature {i}: {str(e)}")
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: ✗ Erreur création feature {i}: {str(e)}", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
        
        # Mettre à jour les extents (la couche n'est pas ajoutée au projet ici)
        layer.updateExtents()
        
        # Log du résultat
        if error_count == 0:
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: ✓ Couche créée avec {success_count} entrées sur {len(descriptions_data)} prévues", 
                "Biblizou", 
                level=Qgis.Success
            )
        else:
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: ⚠ Couche créée avec {success_count} entrées, {error_count} erreurs", 
                "Biblizou", 
                level=Qgis.Warning
            )
            for detail in error_details:
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: Détail erreur: {detail}", 
                    "Biblizou", 
                    level=Qgis.Warning
                )
        
        # Vérifier le nombre d'entités dans la couche
        feature_count_in_layer = layer.featureCount()
        QgsMessageLog.logMessage(
            f"[ZnieffXmlToLayerDesc]: ✓ Nombre d'entités dans la couche: {feature_count_in_layer}", 
            "Biblizou", 
            level=Qgis.Info
        )
        
        return layer

    def save_to_geopackage(self, layer):
        """Enregistre la couche dans un GeoPackage."""
        try:
            gpkg_exists = os.path.exists(self.gpkg_path)
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.driverName = "GPKG"
            save_options.layerName = "Znieff_Descriptions"
            if gpkg_exists:
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: GeoPackage existant trouvé : {self.gpkg_path}",
                    "Biblizou",
                    level=Qgis.Info
                )
            else:
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: Création d'un nouveau GeoPackage : {self.gpkg_path}",
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
                    f"[ZnieffXmlToLayerDesc]: Couche sauvegardée avec succès dans {self.gpkg_path}",
                    "Biblizou",
                    level=Qgis.Success
                )
            else:
                self.gpkg_saved = False
                QgsMessageLog.logMessage(
                    f"[ZnieffXmlToLayerDesc]: Erreur lors de la sauvegarde : {error[1]}",
                    "Biblizou",
                    level=Qgis.Critical
                )
        except Exception as e:
            self.gpkg_saved = False
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: Exception lors de la sauvegarde : {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )

    def load_from_geopackage(self):
        """Charge la couche depuis le GeoPackage dans QGIS."""
        try:
            uri = f"{self.gpkg_path}|layername=Znieff_Descriptions"
            layer = QgsVectorLayer(uri, "Znieff_Descriptions", "ogr")
            if layer.isValid():
                layer.setDisplayExpression("coalesce(LB_ZN, '') || ' (' || coalesce(NM_SFFZN, '') || ')'")
                existing_layers = QgsProject.instance().mapLayersByName("ZNIEFF_Descriptions")
                for existing_layer in existing_layers:
                    QgsProject.instance().removeMapLayer(existing_layer.id())
                QgsProject.instance().addMapLayer(layer)
                QgsMessageLog.logMessage(
                    "[ZnieffXmlToLayerDesc]: Couche chargée depuis le GeoPackage",
                    "Biblizou",
                    level=Qgis.Success
                )
            else:
                QgsMessageLog.logMessage(
                    "[ZnieffXmlToLayerDesc]: Erreur - la couche chargée n'est pas valide",
                    "Biblizou",
                    level=Qgis.Critical
                )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"[ZnieffXmlToLayerDesc]: Erreur lors du chargement : {str(e)}",
                "Biblizou",
                level=Qgis.Critical
            )

    def convert_to_double(self, value):
        """Convertit une valeur en double, retourne None si conversion impossible."""
        if not value:
            return None
        try:
            # Remplacer la virgule par un point pour les nombres français
            value_str = str(value).replace(',', '.').strip()
            # Supprimer les espaces et caractères non numériques sauf le point décimal et le signe négatif
            value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
            if value_str:
                return float(value_str)
            else:
                return None
        except (ValueError, TypeError):
            return None

    def show_summary(self, descriptions_count, actual_count):
        """Affiche un résumé du traitement (mode indépendant uniquement)."""
        if descriptions_count == actual_count:
            summary = (
                f"Résultats du traitement ZNIEFF - Descriptions:\n\n"
                f"• Fichiers XML traités: {self.processed_files}\n"
                f"• Descriptions extraites: {descriptions_count}\n"
                f"• Entrées dans la couche: {actual_count}\n\n"
                f"✓ Couche 'ZNIEFF - Descriptions' créée avec {actual_count} entrées\n"
                f"✓ Contenu HTML généré pour les popups\n\n"
                f"Pour utiliser les descriptions :\n"
                f"1. Ouvrez la table attributaire de la couche\n"
                f"2. Sélectionnez un enregistrement\n"
                f"3. Utilisez l'outil 'Identifier' pour voir le popup HTML"
            )
        else:
            summary = (
                f"Résultats du traitement ZNIEFF - Descriptions:\n\n"
                f"• Fichiers XML traités: {self.processed_files}\n"
                f"• Descriptions extraites: {descriptions_count}\n"
                f"• Entrées dans la couche: {actual_count}\n\n"
                f"✓ Couche 'ZNIEFF - Descriptions' créée\n"
                f"✓ Contenu HTML généré pour les popups\n\n"
                f"Pour utiliser les descriptions :\n"
                f"1. Ouvrez la table attributaire de la couche\n"
                f"2. Sélectionnez un enregistrement\n"
                f"3. Utilisez l'outil 'Identifier' pour voir le popup HTML"
            )
            
        QMessageBox.information(
            None,
            "Traitement ZNIEFF terminé",
            summary
        )
    
        def convert_to_double(self, value):
            """Convertit une valeur en double, retourne None si conversion impossible."""
            if not value:
                return None
            try:
                # Remplacer la virgule par un point pour les nombres français
                value_str = str(value).replace(',', '.').strip()
                # Supprimer les espaces et caractères non numériques sauf le point décimal et le signe négatif
                value_str = ''.join(c for c in value_str if c.isdigit() or c in '.-')
                if value_str:
                    return float(value_str)
                else:
                    return None
            except (ValueError, TypeError):
                return None
            
        def show_summary(self, descriptions_count, actual_count):
            """Affiche un résumé du traitement (mode indépendant uniquement)."""
            if descriptions_count == actual_count:
                summary = (
                    f"Résultats du traitement ZNIEFF - Descriptions:\n\n"
                    f"• Fichiers XML traités: {self.processed_files}\n"
                    f"• Descriptions extraites: {descriptions_count}\n"
                    f"• Entrées dans la couche: {actual_count}\n\n"
                    f"✓ Couche 'ZNIEFF - Descriptions' créée avec {actual_count} entrées\n"
                    f"✓ Contenu HTML généré pour les popups\n\n"
                    f"Pour utiliser les descriptions :\n"
                    f"1. Ouvrez la table attributaire de la couche\n"
                    f"2. Sélectionnez un enregistrement\n"
                    f"3. Utilisez l'outil 'Identifier' pour voir le popup HTML"
                )
            else:
                summary = (
                    f"Résultats du traitement ZNIEFF - Descriptions:\n\n"
                    f"• Fichiers XML traités: {self.processed_files}\n"
                    f"• Descriptions extraites: {descriptions_count}\n"
                    f"• Entrées dans la couche: {actual_count}\n\n"
                    f"✓ Couche 'ZNIEFF - Descriptions' créée\n"
                    f"✓ Contenu HTML généré pour les popups\n\n"
                    f"Pour utiliser les descriptions :\n"
                    f"1. Ouvrez la table attributaire de la couche\n"
                    f"2. Sélectionnez un enregistrement\n"
                    f"3. Utilisez l'outil 'Identifier' pour voir le popup HTML"
                )
                
            QMessageBox.information(
                None,
                "Traitement ZNIEFF terminé",
                summary
            )


# Fonctions d'exécution pour QGIS
def run_module():
    """Fonction d'exécution pour QGIS (mode indépendant)."""
    module = ZnieffXmlToLayerDesc()
    module.run()


def run_module_with_path(folder_path):
    """
    Fonction d'exécution pour BiblizouMain.
    
    Args:
        folder_path (str): Chemin du dossier contenant les fichiers XML ZNIEFF
        
    Returns:
        bool: True si le traitement a réussi, False sinon
    """
    module = ZnieffXmlToLayerDesc()
    return module.run_with_path(folder_path)


# Exécution
if __name__ == "__console__":
    # Mode console: exécuter en mode indépendant
    run_module()