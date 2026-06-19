# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaXmlToLayerDesc.py
Groupe : FSD
Description : Module pour extraire les descriptions des sites Natura 2000 des fichiers XML
              et les exporter dans une couche QGIS enrichie sans géométrie.
"""

import os
import html
import xml.etree.ElementTree as ET

from qgis.core import QgsVectorLayer, QgsFeature, QgsField, Qgis
from qgis.PyQt.QtCore import QVariant

from .base.XmlToLayer import XmlToLayer


class NaturaXmlToLayerDesc(XmlToLayer):
    """
    Extraction des descriptions des sites Natura 2000.

    Implémente les 4 méthodes abstraites de XmlToLayer :
        - get_layer_name()    → "Natura_2000_Descriptions"
        - get_xml_filter()    → fichiers FR*.xml de 13 caractères
        - process_xml_file()  → parsing SITECODE, SITE_NAME, COMMENTAIRE_ROW
        - create_temp_layer() → 5 champs : SITECODE, SITE_NAME, QUALITY, VULNAR, HTML_POPUP

    Surcharge :
        - load_from_geopackage() → applique setDisplayExpression("SITE_NAME")
    """

    def get_layer_name(self) -> str:
        return "Natura_2000_Descriptions"

    def get_xml_filter(self) -> callable:
        return lambda f: f.startswith('FR') and f.endswith('.xml') and len(f) == 13

    def process_xml_file(self, xml_path: str) -> list:
        descriptions_data = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            sitecode = self._text(root.find('SITECODE'))
            site_name = self._text(root.find('SITE_NAME'))

            commentaire_elem = root.find('COMMENTAIRE')
            if commentaire_elem is not None:
                for row in commentaire_elem.findall('COMMENTAIRE_ROW'):
                    quality = ' '.join(self._text(row.find('QUALITY')).split())
                    vulnar = ' '.join(self._text(row.find('VULNAR')).split())

                    descriptions_data.append({
                        'SITECODE': sitecode,
                        'SITE_NAME': site_name,
                        'QUALITY': quality,
                        'VULNAR': vulnar,
                        'HTML_POPUP': self._html_popup(sitecode, site_name, quality, vulnar),
                    })

        except ET.ParseError as e:
            self.log_message(f"Erreur parsing {os.path.basename(xml_path)}: {e}", Qgis.Warning)
        except Exception as e:
            self.log_message(f"Erreur traitement {os.path.basename(xml_path)}: {e}", Qgis.Warning)

        return descriptions_data

    def create_temp_layer(self, descriptions_data: list) -> QgsVectorLayer:
        fields = [
            QgsField('SITECODE', QVariant.String),
            QgsField('SITE_NAME', QVariant.String),
            QgsField('QUALITY', QVariant.String),
            QgsField('VULNAR', QVariant.String),
            QgsField('HTML_POPUP', QVariant.String),
        ]

        layer = QgsVectorLayer("None", f"{self.get_layer_name()}_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        layer.setDisplayExpression("SITE_NAME")

        features = []
        for data in descriptions_data:
            feat = QgsFeature()
            feat.setFields(layer.fields())
            feat.setAttributes([data.get(f.name(), '') for f in layer.fields()])
            features.append(feat)

        provider.addFeatures(features)
        layer.updateExtents()

        self.log_message(
            f"Couche temporaire créée avec {len(descriptions_data)} entrées", Qgis.Success
        )
        return layer

    def load_from_geopackage(self):
        """Surcharge : applique setDisplayExpression après chargement."""
        layer_name = self.get_layer_name()
        try:
            uri = f"{self.gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, layer_name, "ogr")
            if layer.isValid():
                layer.setDisplayExpression("SITE_NAME")
                from qgis.core import QgsProject
                for old in QgsProject.instance().mapLayersByName(layer_name):
                    QgsProject.instance().removeMapLayer(old.id())
                QgsProject.instance().addMapLayer(layer)
                self.log_message("Couche chargée depuis le GeoPackage", Qgis.Success)
            else:
                self.log_message("Couche chargée invalide", Qgis.Critical)
        except Exception as e:
            self.log_message(f"Erreur chargement : {e}", Qgis.Critical)

    # -----------------------------------------------------------------------
    # Helpers privés
    # -----------------------------------------------------------------------

    def _text(self, element) -> str:
        if element is not None and element.text:
            return element.text.strip()
        return ""

    def _html_popup(self, sitecode: str, site_name: str, quality: str, vulnar: str) -> str:
        s_code = html.escape(sitecode)
        s_name = html.escape(site_name)
        s_quality = html.escape(quality).replace('\n', '<br>') if quality else '<i>Aucune information</i>'
        s_vulnar = html.escape(vulnar).replace('\n', '<br>') if vulnar else '<i>Aucune information</i>'

        return f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: Arial, sans-serif; margin: 10px; }}
  .header {{ color: #009999; border-bottom: 2px solid #009999; padding-bottom: 5px; margin-bottom: 15px; }}
  .title {{ font-size: 16px; font-weight: bold; }}
  .subtitle {{ font-size: 14px; color: #666; }}
  .section {{ margin-bottom: 15px; }}
  .section-title {{ font-weight: bold; color: #009999; margin-bottom: 5px; }}
  .content {{ margin-left: 10px; text-align: justify; }}
</style></head>
<body>
  <div class="header">
    <div class="title">{s_name}</div>
    <div class="subtitle">Code : {s_code}</div>
  </div>
  <div class="section">
    <div class="section-title">Valeur écologique (QUALITY) :</div>
    <div class="content">{s_quality}</div>
  </div>
  <div class="section">
    <div class="section-title">Vulnérabilités (VULNAR) :</div>
    <div class="content">{s_vulnar}</div>
  </div>
</body></html>"""


def run_module_with_path(folder_path: str):
    return NaturaXmlToLayerDesc().run_with_path(folder_path)


if __name__ == "__console__":
    NaturaXmlToLayerDesc().run()
