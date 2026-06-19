# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaXmlToLayerHab.py
Groupe : FSD
Description : Module pour extraire des données d'habitats directive à partir de fichiers XML
              et les exporter dans un GeoPackage.
"""

import os
import xml.etree.ElementTree as ET

from qgis.core import QgsVectorLayer, QgsFeature, QgsField, Qgis
from qgis.PyQt.QtCore import QVariant

from .base.XmlToLayer import XmlToLayer


class NaturaXmlToLayerHab(XmlToLayer):
    """
    Extraction des habitats directive Natura 2000 (HABIT1_ROW).

    Implémente les 4 méthodes abstraites de XmlToLayer :
        - get_layer_name()    → "Natura_2000_Habitats"
        - get_xml_filter()    → fichiers FR*.xml de 13 caractères
        - process_xml_file()  → parsing SITECODE, SITE_NAME, HABIT1_ROW
        - create_temp_layer() → 4 champs : SITECODE, SITE_NAME, CD_UE, LB_HABDH_FR
    """

    def get_layer_name(self) -> str:
        return "Natura_2000_Habitats"

    def get_xml_filter(self) -> callable:
        return lambda f: f.startswith('FR') and f.endswith('.xml') and len(f) == 13

    def process_xml_file(self, xml_path: str) -> list:
        habitats_data = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            sitecode = (root.findtext('SITECODE', '') or '').strip()
            site_name = (root.findtext('SITE_NAME', '') or '').strip()

            for row in root.findall('.//HABIT1_ROW'):
                cd_ue = (row.findtext('CD_UE', '') or '').strip()
                lb_habdh_fr = (row.findtext('LB_HABDH_FR', '') or '').strip()

                if cd_ue or lb_habdh_fr:
                    habitats_data.append({
                        'SITECODE': sitecode,
                        'SITE_NAME': site_name,
                        'CD_UE': cd_ue,
                        'LB_HABDH_FR': lb_habdh_fr,
                    })

        except ET.ParseError as e:
            self.log_message(f"Erreur parsing {os.path.basename(xml_path)}: {e}", Qgis.Warning)
        except Exception as e:
            self.log_message(f"Erreur traitement {os.path.basename(xml_path)}: {e}", Qgis.Warning)

        return habitats_data

    def create_temp_layer(self, habitats_data: list) -> QgsVectorLayer:
        fields = [
            QgsField('SITECODE', QVariant.String),
            QgsField('SITE_NAME', QVariant.String),
            QgsField('CD_UE', QVariant.String),
            QgsField('LB_HABDH_FR', QVariant.String),
        ]

        layer = QgsVectorLayer("None", f"{self.get_layer_name()}_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()

        features = []
        for data in habitats_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([data.get(f.name(), '') for f in layer.fields()])
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()

        self.log_message(
            f"Couche temporaire créée avec {len(habitats_data)} habitats", Qgis.Info
        )
        return layer


def run_module_with_path(folder_path: str):
    return NaturaXmlToLayerHab().run_with_path(folder_path)


if __name__ == "__console__":
    NaturaXmlToLayerHab().run()
