# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaPivotHabitats.py
Groupe : FSD
Description : Module pour créer un tableau croisé dynamique (pivot) des habitats Natura 2000.
              Transforme la table longue en format large avec un site par colonne.

"""

import unicodedata
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsMessageLog,
    Qgis
)
from PyQt5.QtWidgets import QMessageBox

class NaturaPivotHabitats:
    """Classe pour créer un tableau croisé dynamique des habitats Natura 2000."""
    
    def __init__(self, source_layer_name="Natura_2000_Habitats", 
                 output_layer_name="Natura_2000_Habitats_Pivot"):
        """
        Initialisation de la classe.
        
        Args:
            source_layer_name (str): Nom de la couche source contenant les habitats
            output_layer_name (str): Nom de la couche pivot à créer
        """
        self.source_layer_name = source_layer_name
        self.output_layer_name = output_layer_name
        self.source_layer = None
        # code -> nom du site (pour colonnes [code] - [NOM_SITE])
        self.site_by_code = {}

    def remove_accents(self, text):
        """Supprime les accents (à, â, é, è, ë, ê, î, ô, ù...)."""
        if not text:
            return text
        nfd = unicodedata.normalize('NFD', str(text))
        return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
        
    def run(self):
        """Point d'entrée principal du module."""
        # 1. Vérifier et charger la couche source
        if not self.load_source_layer():
            return False
            
        # 2. Extraire les sites uniques (code -> nom)
        if not self.extract_unique_sites():
            return False
            
        # 3. Construire la requête SQL dynamique
        sql_query = self.build_pivot_query()
        
        if not sql_query:
            return False
            
        # 4. Créer la couche virtuelle pivot
        if not self.create_virtual_layer(sql_query):
            return False
            
        # 5. Afficher le résumé
        # self.show_summary()
        
        return True
        
    def load_source_layer(self):
        """
        Charge la couche source depuis le projet QGIS.
        
        Returns:
            bool: True si la couche est trouvée et valide, False sinon
        """
        layers = QgsProject.instance().mapLayersByName(self.source_layer_name)
        
        if not layers:
            QgsMessageLog.logMessage(
                f"Erreur : Couche '{self.source_layer_name}' introuvable dans le projet", 
                "Biblizou", 
                level=Qgis.Critical
            )
            QMessageBox.warning(
                None,
                "Couche introuvable",
                f"La couche '{self.source_layer_name}' n'existe pas dans le projet.\n\n"
                f"Veuillez d'abord exécuter le module d'import des habitats."
            )
            return False
            
        self.source_layer = layers[0]
        
        if not self.source_layer.isValid():
            QgsMessageLog.logMessage(
                f"Erreur : La couche '{self.source_layer_name}' n'est pas valide", 
                "Biblizou", 
                level=Qgis.Critical
            )
            QMessageBox.warning(
                None,
                "Couche invalide",
                f"La couche '{self.source_layer_name}' n'est pas valide."
            )
            return False
            
        QgsMessageLog.logMessage(
            f"Couche source '{self.source_layer_name}' chargée avec succès", 
            "Biblizou", 
            level=Qgis.Info
        )
        return True
        
    def extract_unique_sites(self):
        """
        Extrait tous les couples (SITECODE, SITE_NAME) uniques de la couche source.
        
        Returns:
            bool: True si au moins un site est trouvé, False sinon
        """
        try:
            feature_count = self.source_layer.featureCount()
            
            if feature_count == 0:
                QMessageBox.warning(
                    None,
                    "Couche vide",
                    f"La couche '{self.source_layer_name}' ne contient aucun enregistrement."
                )
                return False
            
            QgsMessageLog.logMessage(
                f"Extraction des sites uniques depuis {feature_count} enregistrements",
                "Biblizou",
                level=Qgis.Info
            )
            
            for feature in self.source_layer.getFeatures():
                site_code = feature['SITECODE']
                site_name = feature['SITE_NAME']
                if site_code:
                    self.site_by_code[site_code] = site_name if site_name else "Sans nom"
            
            if not self.site_by_code:
                QgsMessageLog.logMessage(
                    "Aucun site trouvé dans la couche",
                    "Biblizou",
                    level=Qgis.Warning
                )
                QMessageBox.warning(
                    None,
                    "Aucun site",
                    "Aucun code de site valide trouvé dans la couche."
                )
                return False
                
            QgsMessageLog.logMessage(
                f"{len(self.site_by_code)} sites uniques trouvés",
                "Biblizou",
                level=Qgis.Success
            )
            return True
            
        except KeyError as e:
            QgsMessageLog.logMessage(
                f"Erreur : Champ manquant dans la couche (SITECODE ou SITE_NAME) : {e}",
                "Biblizou",
                level=Qgis.Critical
            )
            QMessageBox.critical(
                None,
                "Erreur de structure",
                "Les champs 'SITECODE' et 'SITE_NAME' doivent être présents dans la couche."
            )
            return False
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Erreur lors de l'extraction des sites : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
            QMessageBox.critical(
                None,
                "Erreur",
                f"Une erreur s'est produite lors de l'extraction des sites :\n{str(e)}"
            )
            return False
            
    def build_pivot_query(self):
        """
        Construit la requête SQL pour créer le tableau croisé dynamique.
        Colonnes au format [code] - [NOM_SITE] (NOM_SITE en majuscules, sans accents).
        
        Returns:
            str: La requête SQL complète, ou None en cas d'erreur
        """
        try:
            case_statements = []
            for code, name in sorted(self.site_by_code.items()):
                # NOM_SITE : majuscules et sans diacritiques (à, â, é, è, ë, ê, î, ô, ù...)
                nom_site = self.remove_accents(str(name)).upper()
                escaped_code = str(code).replace("'", "''")
                col_alias = f"{code} - {nom_site}".replace('"', '""')
                case_statements.append(
                    f"MAX(CASE WHEN SITECODE = '{escaped_code}' THEN 1 END) AS \"{col_alias}\""
                )
            
            sql_query = f"""
SELECT 
    CD_UE,
    LB_HABDH_FR,
    {', '.join(case_statements)}
FROM "{self.source_layer_name}"
GROUP BY CD_UE, LB_HABDH_FR
ORDER BY CD_UE
"""
            
            QgsMessageLog.logMessage(
                f"Requête SQL générée avec {len(case_statements)} colonnes [code] - [NOM_SITE]",
                "Biblizou",
                level=Qgis.Info
            )
            
            return sql_query
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Erreur lors de la construction de la requête : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
            return None
            
    def create_virtual_layer(self, sql_query):
        """
        Crée la couche virtuelle pivot et l'ajoute au projet.
        
        Args:
            sql_query (str): La requête SQL pour créer le pivot
            
        Returns:
            bool: True si la couche est créée avec succès, False sinon
        """
        try:
            # Créer la couche virtuelle
            virtual_layer = QgsVectorLayer(
                f"?query={sql_query}",
                self.output_layer_name,
                "virtual"
            )
            
            if not virtual_layer.isValid():
                QgsMessageLog.logMessage(
                    "Erreur : La couche virtuelle créée n'est pas valide", 
                    "Biblizou", 
                    level=Qgis.Critical
                )
                QMessageBox.critical(
                    None,
                    "Erreur de création",
                    "La couche virtuelle n'a pas pu être créée.\n"
                    "Vérifiez la structure de la couche source."
                )
                return False
            
            # Supprimer l'ancienne couche pivot si elle existe
            existing_layers = QgsProject.instance().mapLayersByName(self.output_layer_name)
            for existing_layer in existing_layers:
                QgsProject.instance().removeMapLayer(existing_layer.id())
                QgsMessageLog.logMessage(
                    f"Ancienne couche '{self.output_layer_name}' supprimée", 
                    "Biblizou", 
                    level=Qgis.Info
                )
            
            # Ajouter la nouvelle couche au projet
            QgsProject.instance().addMapLayer(virtual_layer)
            
            QgsMessageLog.logMessage(
                f"Couche virtuelle '{self.output_layer_name}' créée avec succès "
                f"({virtual_layer.featureCount()} habitats)", 
                "Biblizou", 
                level=Qgis.Success
            )
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Erreur lors de la création de la couche virtuelle : {str(e)}", 
                "Biblizou", 
                level=Qgis.Critical
            )
            QMessageBox.critical(
                None,
                "Erreur",
                f"Erreur lors de la création de la couche virtuelle :\n{str(e)}"
            )
            return False
            
    def show_summary(self):
        """Affiche un résumé de l'opération."""
        summary = (
            f"Tableau croisé créé avec succès !\n\n"
            f"• Couche source : {self.source_layer_name}\n"
            f"• Couche créée : {self.output_layer_name}\n"
            f"• Nombre de sites (colonnes) : {len(self.site_by_code)}\n"
            f"• Type : Couche virtuelle\n\n"
            f"✓ Les valeurs '1' indiquent la présence de l'habitat dans le site"
        )
        
        QMessageBox.information(
            None,
            "Pivot créé",
            summary
        )
        
        # Optionnel : afficher la liste des sites dans le log
        QgsMessageLog.logMessage(
            f"Sites inclus : {', '.join(sorted(self.site_by_code.keys()))}",
            "Biblizou",
            level=Qgis.Info
        )


# Pour exécuter le module dans QGIS
def run_module():
    """Fonction d'exécution pour QGIS."""
    pivot = NaturaPivotHabitats()
    success = pivot.run()
    
    if success:
        print("Couche virtuelle pivot créée avec succès !")
    else:
        print("Échec de la création de la couche pivot.")


# Exécution
if __name__ == "__console__":
    run_module()