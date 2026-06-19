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

from qgis.core import QgsVectorLayer, QgsFeature, QgsField, Qgis
from qgis.PyQt.QtCore import QVariant

from .base.XmlToLayer import XmlToLayer


class ZnieffXmlToLayerHab(XmlToLayer):
    """
    Extraction des habitats déterminants ZNIEFF (FG_TYPO = 'D').

    Implémente les 4 méthodes abstraites de XmlToLayer :
        - get_layer_name()    → "Znieff_Habitats"
        - get_xml_filter()    → fichiers XML ZNIEFF (pas de préfixe FR, 13 caractères)
        - process_xml_file()  → parsing des balises ZNIEFF/TYPO_INFO_ROW
        - create_temp_layer() → champs NM_SFFZN, LB_ZN, LB_CODE, LB_HAB
    """

    def get_layer_name(self) -> str:
        return "Znieff_Habitats"

    def get_xml_filter(self) -> callable:
        """Fichiers XML ZNIEFF : 13 caractères, sans préfixe FR."""
        return lambda f: f.endswith('.xml') and not f.startswith('FR') and len(f) == 13

    def process_xml_file(self, xml_path: str) -> list:
        """
        Parse un fichier XML ZNIEFF et extrait les habitats déterminants (FG_TYPO = 'D').

        Returns:
            list: liste de dicts avec les clés NM_SFFZN, LB_ZN, LB_CODE, LB_HAB
        """
        habitats_data = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for znieff_elem in root.iter('ZNIEFF'):
                nm_sffzn = ""
                lb_zn = ""

                nm_sffzn_elem = znieff_elem.find('NM_SFFZN')
                lb_zn_elem = znieff_elem.find('LB_ZN')

                if nm_sffzn_elem is not None:
                    nm_sffzn = nm_sffzn_elem.text or ""
                if lb_zn_elem is not None:
                    lb_zn = lb_zn_elem.text or ""

                for typo_info_row_elem in znieff_elem.iter('TYPO_INFO_ROW'):
                    fg_typo_elem = typo_info_row_elem.find('FG_TYPO')

                    # Habitats déterminants uniquement
                    if fg_typo_elem is not None and fg_typo_elem.text == 'D':
                        codes_in_row = [
                            e.text for e in typo_info_row_elem.iter('LB_CODE') if e.text
                        ]
                        habs_in_row = [
                            e.text for e in typo_info_row_elem.iter('LB_HAB') if e.text
                        ]

                        for i in range(max(len(codes_in_row), len(habs_in_row))):
                            habitats_data.append({
                                'NM_SFFZN': nm_sffzn,
                                'LB_ZN':    lb_zn,
                                'LB_CODE':  codes_in_row[i] if i < len(codes_in_row) else "",
                                'LB_HAB':   habs_in_row[i]  if i < len(habs_in_row)  else ""
                            })

        except ET.ParseError as e:
            self.log_message(
                f"Erreur de parsing XML {os.path.basename(xml_path)}: {e}", Qgis.Warning
            )
        except Exception as e:
            self.log_message(
                f"Erreur traitement {os.path.basename(xml_path)}: {e}", Qgis.Warning
            )

        return habitats_data

    def create_temp_layer(self, habitats_data: list) -> QgsVectorLayer:
        """
        Crée une couche mémoire QGIS sans géométrie avec les champs habitats ZNIEFF.
        """
        fields = [
            QgsField('NM_SFFZN', QVariant.String),  # Numéro ZNIEFF
            QgsField('LB_ZN',    QVariant.String),  # Nom ZNIEFF
            QgsField('LB_CODE',  QVariant.String),  # Code habitat
            QgsField('LB_HAB',   QVariant.String),  # Libellé habitat
        ]

        layer = QgsVectorLayer("None", f"{self.get_layer_name()}_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()

        features = []
        for data in habitats_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([
                data.get('NM_SFFZN', ''),
                data.get('LB_ZN',    ''),
                data.get('LB_CODE',  ''),
                data.get('LB_HAB',   ''),
            ])
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()

        self.log_message(
            f"Couche temporaire créée avec {len(habitats_data)} enregistrements", Qgis.Info
        )
        return layer


# ---------------------------------------------------------------------------
# Fonctions d'entrée
# ---------------------------------------------------------------------------

def run_module_with_path(folder_path: str):
    """Mode BiblizouMain."""
    return ZnieffXmlToLayerHab().run_with_path(folder_path)


if __name__ == "__console__":
    run_module()