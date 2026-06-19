# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : ZnieffXmlToLayerEsp.py
Groupe : FSD
Description : Module pour extraire les données d'espèces à partir des XML ZNIEFF
              et les exporter dans un GeoPackage (Mode Offline).
"""

import os
import xml.etree.ElementTree as ET

from qgis.core import QgsVectorLayer, QgsFeature, QgsField, Qgis
from qgis.PyQt.QtCore import QVariant

from .base.XmlToLayer import XmlToLayer


class ZnieffXmlToLayerEsp(XmlToLayer):
    """
    Extraction des espèces ZNIEFF.

    Implémente les 4 méthodes abstraites de XmlToLayer :
        - get_layer_name()    → "Znieff_Especes"
        - get_xml_filter()    → fichiers XML ZNIEFF (pas de préfixe FR, 13 caractères)
        - process_xml_file()  → parsing des balises ESPECE_PROJET_ROW / ESPECE_ROW
        - create_temp_layer() → 12 champs espèces ZNIEFF
    """

    def get_layer_name(self) -> str:
        return "Znieff_Especes"

    def get_xml_filter(self) -> callable:
        return lambda f: f.endswith('.xml') and not f.startswith('FR') and len(f) == 13

    def process_xml_file(self, xml_path: str) -> list:
        species_data = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            nm_sffzn = root.findtext('NM_SFFZN', '').strip()
            lb_zn    = root.findtext('LB_ZN', '').strip()

            for species_row in root.iter():
                if species_row.tag in ['ESPECE_PROJET_ROW', 'ESPECE_ROW']:
                    species_data.append({
                        'regne':      species_row.findtext('REGNE',      '').strip(),
                        'groupe':     species_row.findtext('GROUPE',     '').strip(),
                        'cd_nom':     species_row.findtext('CD_NOM',     '').strip(),
                        'fg_conf':    species_row.findtext('FG_CONF',    '').strip(),
                        'fg_esp':     species_row.findtext('FG_ESP',     '').strip(),
                        'nm_sffzn':   species_row.findtext('NM_SFFZN',  nm_sffzn).strip(),
                        'date_crea':  species_row.findtext('DATE_CREA',  '').strip(),
                        'date_modif': species_row.findtext('DATE_MODIF', '').strip(),
                        'nom_complet':species_row.findtext('NOM_COMPLET','').strip(),
                        'nom_vern':   species_row.findtext('NOM_VERN',   '').strip(),
                        'origine':    species_row.findtext('ORIGINE',    '').strip(),
                        'lb_zn':      lb_zn,
                    })

        except ET.ParseError as e:
            self.log_message(f"Erreur parsing {os.path.basename(xml_path)}: {e}", Qgis.Warning)
        except Exception as e:
            self.log_message(f"Erreur traitement {os.path.basename(xml_path)}: {e}", Qgis.Warning)

        return species_data

    def create_temp_layer(self, species_data: list) -> QgsVectorLayer:
        fields = [
            QgsField('regne',       QVariant.String),
            QgsField('groupe',      QVariant.String),
            QgsField('cd_nom',      QVariant.String),
            QgsField('fg_conf',     QVariant.String),
            QgsField('fg_esp',      QVariant.String),
            QgsField('nm_sffzn',    QVariant.String),
            QgsField('date_crea',   QVariant.String),
            QgsField('date_modif',  QVariant.String),
            QgsField('nom_complet', QVariant.String),
            QgsField('nom_vern',    QVariant.String),
            QgsField('origine',     QVariant.String),
            QgsField('lb_zn',       QVariant.String),
        ]

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
    return ZnieffXmlToLayerEsp().run_with_path(folder_path)


if __name__ == "__console__":
    ZnieffXmlToLayerEsp().run()