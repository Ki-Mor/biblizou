"""
Auteur : ExEco Environnement - François Botcazou
Date : 2025/03
Version : 1.4
Nom : ZnieffPivotEspeces.py
Groupe : Biblizou_PatNat
Description : Module pour créer un tableau croisé dynamique (pivot) unique des espèces ZNIEFF.
              Filtré uniquement sur les espèces déterminantes (FG_ESP = 'D').
              - GROUPE en première colonne
              - cd_noms, nom_complets, nom_vern en colonnes suivantes.
              - Sites en colonnes nommées "[nm_sffzn] - [lb_zn]" (sans accents).
              - Valeurs NULL au lieu de 0 pour la clarté visuelle.
              - Tri par GROUPE puis par nom_complet (ascendant).
"""

import unicodedata
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsMessageLog,
    Qgis
)
from PyQt5.QtWidgets import QMessageBox


class ZnieffPivotEspeces:
    """Classe pour créer un tableau croisé unique pour toutes les espèces déterminantes ZNIEFF."""
    
    def __init__(self, source_layer_name="Znieff_Especes"):
        """Initialisation."""
        self.source_layer_name = source_layer_name
        self.output_layer_name = "Znieff_EspDet_Pivot"

    def remove_accents(self, text):
        """Supprime les accents d'une chaîne de caractères."""
        if not text:
            return text
        # Normalisation NFD (décomposition) puis suppression des marques diacritiques
        nfd = unicodedata.normalize('NFD', str(text))
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')

    def run(self):
        """Exécute la création du pivot unique."""
        # 1. Récupérer la couche source
        source_layers = QgsProject.instance().mapLayersByName(self.source_layer_name)
        
        if not source_layers:
            QgsMessageLog.logMessage(f"Erreur : Couche '{self.source_layer_name}' introuvable.", "Biblizou", level=Qgis.Critical)
            return False

        source_layer = source_layers[0]
        
        # 2. Vérifier que le champ FG_ESP existe
        if source_layer.fields().indexOf('fg_esp') == -1:
            QgsMessageLog.logMessage(f"Erreur : Champ 'fg_esp' introuvable.", "Biblizou", level=Qgis.Critical)
            return False
        
        # 3. Créer le pivot unique
        success = self.create_pivot(source_layer)
        
        if success:
            QgsMessageLog.logMessage(f"Pivot unique créé : {self.output_layer_name}", "Biblizou", level=Qgis.Success)
        
        return success

    def get_all_sites_for_determinant_species(self, layer):
        """Récupère tous les couples (nm_sffzn, lb_zn) uniques pour les espèces déterminantes."""
        site_info = {}
        for feature in layer.getFeatures():
            # Filtrer uniquement les espèces déterminantes
            if feature['fg_esp'] == 'D':
                code = feature['nm_sffzn']
                name = feature['lb_zn']
                if code:
                    site_info[code] = name if name else "Nom inconnu"
        return site_info

    def create_pivot(self, source_layer):
        """Crée une couche virtuelle pivot unique pour tous les groupes (espèces déterminantes uniquement)."""
        
        # Récupérer tous les sites pour toutes les espèces déterminantes
        sites_dict = self.get_all_sites_for_determinant_species(source_layer)
        if not sites_dict:
            QgsMessageLog.logMessage("Aucun site trouvé pour les espèces déterminantes", "Biblizou", level=Qgis.Warning)
            return False

        # Construction de la requête SQL avec GROUPE en première colonne
        # On utilise l'ID de la couche source au lieu du nom
        layer_id = source_layer.id()
        
        query = "SELECT groupe AS GROUPE, cd_nom, nom_complet, nom_vern"
        
        # Colonnes pivotées : [code] - [NOM_SITE] (NOM_SITE en majuscules, sans accents)
        for site_code in sorted(sites_dict.keys()):
            site_label = sites_dict[site_code]
            
            safe_code = site_code.replace("'", "''")
            # NOM_SITE : majuscules et sans diacritiques (à, â, é, è, ë, ê, î, ô, ù...)
            nom_site = self.remove_accents(str(site_label)).upper()
            column_alias = f"{site_code} - {nom_site}".replace('"', '""')
            
            # CASE : 1 si présent, NULL (vide) sinon
            query += f', MAX(CASE WHEN nm_sffzn = \'{safe_code}\' THEN 1 ELSE NULL END) AS "{column_alias}"'
        
        # Filtrer uniquement les espèces déterminantes - utiliser l'ID de la couche
        query += f' FROM "{layer_id}"'
        query += " WHERE fg_esp = 'D'"
        query += " GROUP BY groupe, cd_nom, nom_complet, nom_vern"
        # Tri par groupe puis par nom scientifique
        query += " ORDER BY groupe ASC, nom_complet ASC"

        uri = f"?query={query}"
        
        # Log de la requête pour débogage (premiers caractères uniquement)
        QgsMessageLog.logMessage(f"Requête SQL (début) : {query[:500]}", "Biblizou", level=Qgis.Info)
        
        vlayer = QgsVectorLayer(uri, self.output_layer_name, "virtual")
        
        if vlayer.isValid():
            # Nettoyage si doublon
            existing_layers = QgsProject.instance().mapLayersByName(self.output_layer_name)
            for old_layer in existing_layers:
                QgsProject.instance().removeMapLayer(old_layer.id())
                
            QgsProject.instance().addMapLayer(vlayer)
            QgsMessageLog.logMessage(f"Pivot unique créé avec succès", "Biblizou", level=Qgis.Info)
            return True
        else:
            QgsMessageLog.logMessage(f"Erreur SQL pour le pivot unifié", "Biblizou", level=Qgis.Critical)
            return False
            
    def show_summary(self):
        """Affiche un résumé final."""
        msg = "Tableau croisé ZNIEFF créé avec succès :\n\n"
        msg += "• FILTRE : Espèces déterminantes uniquement (FG_ESP = 'D')\n"
        msg += "• Colonnes : GROUPE, cd_nom, nom_complet, nom_vern\n"
        msg += "• En-têtes : [code] - [NOM_SITE] (majuscules, sans accents)\n"
        msg += "• Absences : Cellules vides\n"
        msg += "• Tri : Par GROUPE puis nom scientifique (ascendant)\n\n"
        msg += f"• {self.output_layer_name}\n"
        
        QMessageBox.information(None, "Pivot ZNIEFF (espèces déterminantes) terminé", msg)


def run_module():
    """Lancement du module."""
    pivot = ZnieffPivotEspeces()
    return pivot.run()

if __name__ == "__console__":
    run_module()