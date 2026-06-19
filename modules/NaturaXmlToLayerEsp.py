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

from qgis.core import QgsVectorLayer, QgsFeature, QgsField, Qgis
from qgis.PyQt.QtCore import QVariant

from .base.XmlToLayer import XmlToLayer


class NaturaXmlToLayerEsp(XmlToLayer):
    """
    Extraction des espèces Natura 2000 (SPECIES_ROW).

    Implémente les 4 méthodes abstraites de XmlToLayer :
        - get_layer_name()    → "Natura_2000_Especes"
        - get_xml_filter()    → fichiers FR*.xml de 13 caractères
        - process_xml_file()  → parsing BIOTOP/SPECIES/SPECIES_ROW (41 champs)
        - create_temp_layer() → 41 champs String
    """

    def get_layer_name(self) -> str:
        return "Natura_2000_Especes"

    def get_xml_filter(self) -> callable:
        return lambda f: f.startswith('FR') and f.endswith('.xml') and len(f) == 13

    def process_xml_file(self, xml_path: str) -> list:
        species_data = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for biotop_elem in root.iter('BIOTOP'):
                sitecode = (biotop_elem.findtext('SITECODE', '') or '').strip()
                site_name = (biotop_elem.findtext('SITE_NAME', '') or '').strip()

                for species_elem in biotop_elem.iter('SPECIES'):
                    for row in species_elem.iter('SPECIES_ROW'):
                        species_data.append({
                            'SITECODE': sitecode,
                            'SITE_NAME': site_name,
                            'PK_SPECIES': (row.findtext('PK_SPECIES', '') or '').strip(),
                            'FPK_NATURA': (row.findtext('FPK_NATURA', '') or '').strip(),
                            'CODE_N2000': (row.findtext('CODE_N2000', '') or '').strip(),
                            'CD_NOM': (row.findtext('CD_NOM', '') or '').strip(),
                            'ANNEXE_II': (row.findtext('ANNEXE_II', '') or '').strip(),
                            'TAXGROUP': (row.findtext('TAXGROUP', '') or '').strip(),
                            'TAX_CODE': (row.findtext('TAX_CODE', '') or '').strip(),
                            'S': (row.findtext('S', '') or '').strip(),
                            'NP': (row.findtext('NP', '') or '').strip(),
                            'TYPE': (row.findtext('TYPE', '') or '').strip(),
                            'SIZE_MIN': (row.findtext('SIZE_MIN', '') or '').strip(),
                            'SIZE_MAX': (row.findtext('SIZE_MAX', '') or '').strip(),
                            'UNIT': (row.findtext('UNIT', '') or '').strip(),
                            'CAT_POP': (row.findtext('CAT_POP', '') or '').strip(),
                            'QUALITY': (row.findtext('QUALITY', '') or '').strip(),
                            'POPULATION': (row.findtext('POPULATION', '') or '').strip(),
                            'CONSERVE': (row.findtext('CONSERVE', '') or '').strip(),
                            'ISOLATION': (row.findtext('ISOLATION', '') or '').strip(),
                            'GLOBAL': (row.findtext('GLOBAL', '') or '').strip(),
                            'CONSERVE_HABITAT': (row.findtext('CONSERVE_HABITAT', '') or '').strip(),
                            'CONSERVE_RESTAURATION': (row.findtext('CONSERVE_RESTAURATION', '') or '').strip(),
                            'DATE_CREA': (row.findtext('DATE_CREA', '') or '').strip(),
                            'DATE_MODIF': (row.findtext('DATE_MODIF', '') or '').strip(),
                            'DATE_SUPP': (row.findtext('DATE_SUPP', '') or '').strip(),
                            'DATE_BASE': (row.findtext('DATE_BASE', '') or '').strip(),
                            'JUSTIFICATION_SUPP': (row.findtext('JUSTIFICATION_SUPP', '') or '').strip(),
                            'COMMENTAIRE_SUPP': (row.findtext('COMMENTAIRE_SUPP', '') or '').strip(),
                            'JUSTIFICATION_SENSIBLE': (row.findtext('JUSTIFICATION_SENSIBLE', '') or '').strip(),
                            'COMMENTAIRE_GENERAL': (row.findtext('COMMENTAIRE_GENERAL', '') or '').strip(),
                            'ALIMENTATION': (row.findtext('ALIMENTATION', '') or '').strip(),
                            'PRES_ACONFIRMER': (row.findtext('PRES_ACONFIRMER', '') or '').strip(),
                            'INVENTAIRE_ANNEE': (row.findtext('INVENTAIRE_ANNEE', '') or '').strip(),
                            'INVENTAIRE_AUTEUR': (row.findtext('INVENTAIRE_AUTEUR', '') or '').strip(),
                            'TENDANCE_CRITERE_STRUCT_FONCT': (
                                        row.findtext('TENDANCE_CRITERE_STRUCT_FONCT', '') or '').strip(),
                            'TENDANCE_CRITERE_AUTRE': (row.findtext('TENDANCE_CRITERE_AUTRE', '') or '').strip(),
                            'TENDANCE_COMMENTAIRE': (row.findtext('TENDANCE_COMMENTAIRE', '') or '').strip(),
                            'TENDANCE': (row.findtext('TENDANCE', '') or '').strip(),
                            'TENDANCE_CRITERE_SURFACE': (row.findtext('TENDANCE_CRITERE_SURFACE', '') or '').strip(),
                            'INVENTAIRE_ANNEE_MIN': (row.findtext('INVENTAIRE_ANNEE_MIN', '') or '').strip(),
                            'UUID_SPECIES': (row.findtext('UUID_SPECIES', '') or '').strip(),
                            'NOM': (row.findtext('NOM', '') or '').strip(),
                        })

        except ET.ParseError as e:
            self.log_message(f"Erreur parsing {os.path.basename(xml_path)}: {e}", Qgis.Warning)
        except Exception as e:
            self.log_message(f"Erreur traitement {os.path.basename(xml_path)}: {e}", Qgis.Warning)

        return species_data

    def create_temp_layer(self, species_data: list) -> QgsVectorLayer:
        field_names = [
            'SITECODE', 'SITE_NAME', 'PK_SPECIES', 'FPK_NATURA', 'CODE_N2000',
            'CD_NOM', 'ANNEXE_II', 'TAXGROUP', 'TAX_CODE', 'S', 'NP', 'TYPE',
            'SIZE_MIN', 'SIZE_MAX', 'UNIT', 'CAT_POP', 'QUALITY', 'POPULATION',
            'CONSERVE', 'ISOLATION', 'GLOBAL', 'CONSERVE_HABITAT', 'CONSERVE_RESTAURATION',
            'DATE_CREA', 'DATE_MODIF', 'DATE_SUPP', 'DATE_BASE',
            'JUSTIFICATION_SUPP', 'COMMENTAIRE_SUPP', 'JUSTIFICATION_SENSIBLE',
            'COMMENTAIRE_GENERAL', 'ALIMENTATION', 'PRES_ACONFIRMER',
            'INVENTAIRE_ANNEE', 'INVENTAIRE_AUTEUR',
            'TENDANCE_CRITERE_STRUCT_FONCT', 'TENDANCE_CRITERE_AUTRE',
            'TENDANCE_COMMENTAIRE', 'TENDANCE', 'TENDANCE_CRITERE_SURFACE',
            'INVENTAIRE_ANNEE_MIN', 'UUID_SPECIES', 'NOM',
        ]

        fields = [QgsField(name, QVariant.String) for name in field_names]

        layer = QgsVectorLayer("None", f"{self.get_layer_name()}_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()

        features = []
        for data in species_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([data.get(f.name(), '') for f in layer.fields()])
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()

        self.log_message(
            f"Couche temporaire créée avec {len(species_data)} espèces", Qgis.Info
        )
        return layer


def run_module_with_path(folder_path: str):
    return NaturaXmlToLayerEsp().run_with_path(folder_path)


if __name__ == "__console__":
    NaturaXmlToLayerEsp().run()
