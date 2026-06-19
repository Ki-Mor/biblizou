# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : ZnieffXmlToLayerDesc.py
Groupe : FSD
Description : Module pour extraire les descriptions des sites ZNIEFF des fichiers XML
              et les exporter dans une couche QGIS enrichie sans géométrie.
"""

import os
import html
import xml.etree.ElementTree as ET

from qgis.core import QgsVectorLayer, QgsFeature, QgsField, Qgis
from qgis.PyQt.QtCore import QVariant

from .base.XmlToLayer import XmlToLayer


class ZnieffXmlToLayerDesc(XmlToLayer):
    """
    Extraction des descriptions ZNIEFF.

    Implémente les 4 méthodes abstraites de XmlToLayer :
        - get_layer_name()    → "Znieff_Descriptions"
        - get_xml_filter()    → tous les fichiers XML du dossier
        - process_xml_file()  → parsing complet des balises ZNIEFF
        - create_temp_layer() → 39 champs descriptions + HTML popup

    Surcharge :
        - load_from_geopackage() → applique setDisplayExpression après chargement
    """

    def get_layer_name(self) -> str:
        return "Znieff_Descriptions"

    def get_xml_filter(self) -> callable:
        """Tous les fichiers XML du dossier (ZNIEFF n'a pas de préfixe standard)."""
        return lambda f: f.endswith('.xml')

    def process_xml_file(self, xml_path: str) -> list:
        descriptions_data = []

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for znieff_elem in root.iter('ZNIEFF'):
                nm_sffzn = self._text(znieff_elem.find('NM_SFFZN'))
                lb_zn = self._text(znieff_elem.find('LB_ZN'))
                tx_gene = self._rich_text(znieff_elem.find('TX_GENE'))

                if not (nm_sffzn or lb_zn or tx_gene):
                    continue

                zni_data = self._extract_zni(znieff_elem)

                descriptions_data.append({
                    'NM_SFFZN': nm_sffzn,
                    'VOLET_ZNIEFF': self._text(znieff_elem.find('VOLET_ZNIEFF')),
                    'TERRITOIRE': self._text(znieff_elem.find('TERRITOIRE')),
                    'NM_SFFZN_PARENT': self._text(znieff_elem.find('NM_SFFZN_PARENT')),
                    'NM_REGZN': self._text(znieff_elem.find('NM_REGZN')),
                    'LB_ZN': lb_zn,
                    'TY_ZONE': self._text(znieff_elem.find('TY_ZONE')),
                    'SU_ZN': self._text(znieff_elem.find('SU_ZN')),
                    'PROF_MINI': self._text(znieff_elem.find('PROF_MINI')),
                    'PROF_MAXI': self._text(znieff_elem.find('PROF_MAXI')),
                    'ALT_MINI': self._text(znieff_elem.find('ALT_MINI')),
                    'ALT_MAXI': self._text(znieff_elem.find('ALT_MAXI')),
                    'X_L2E': self._text(znieff_elem.find('X_L2E')),
                    'Y_L2E': self._text(znieff_elem.find('Y_L2E')),
                    'FG_EVOL': self._text(znieff_elem.find('FG_EVOL')),
                    'FG_EVOL_ANC': self._text(znieff_elem.find('FG_EVOL_ANC')),
                    'FG_CONTOUR': self._text(znieff_elem.find('FG_CONTOUR')),
                    'TX_GEO': self._rich_text(znieff_elem.find('TX_GEO')),
                    'TX_ACTH': self._rich_text(znieff_elem.find('TX_ACTH')),
                    'TX_MESPRO': self._rich_text(znieff_elem.find('TX_MESPRO')),
                    'TX_HYDRO': self._rich_text(znieff_elem.find('TX_HYDRO')),
                    'TX_GRANULO': self._rich_text(znieff_elem.find('TX_GRANULO')),
                    'TX_INTERET': self._rich_text(znieff_elem.find('TX_INTERET')),
                    'TX_FACT': self._rich_text(znieff_elem.find('TX_FACT')),
                    'DESCRIPTION': tx_gene,
                    'TX_DELIM': self._rich_text(znieff_elem.find('TX_DELIM')),
                    'TX_TYPO': self._rich_text(znieff_elem.find('TX_TYPO')),
                    'FG_SUPP': self._text(znieff_elem.find('FG_SUPP')),
                    'DATE_CREA': self._text(znieff_elem.find('DATE_CREA')),
                    'DATE_MODIF': self._text(znieff_elem.find('DATE_MODIF')),
                    'TYPE1_INCLU': self._text(znieff_elem.find('TYPE1_INCLU')),
                    'INCLU_DANS_TYPE2': self._text(znieff_elem.find('INCLU_DANS_TYPE2')),
                    'ZNI_ID_ZNIEFF': zni_data.get('ID_ZNIEFF', ''),
                    'ZNI_NM_SFFZN': zni_data.get('NM_SFFZN', ''),
                    'ZNI_LB_ZN': zni_data.get('LB_ZN', ''),
                    'ZNI_TY_ZONE': zni_data.get('TY_ZONE', ''),
                    'ZNI_NM_REGZN': zni_data.get('NM_REGZN', ''),
                    'ZNI_VOLET_ZNIEFF': zni_data.get('VOLET_ZNIEFF', ''),
                    'HTML_POPUP': self._html_popup(nm_sffzn, lb_zn, tx_gene),
                })

                self.log_message(f"Description extraite : {lb_zn} ({nm_sffzn})", Qgis.Info)

        except ET.ParseError as e:
            self.log_message(f"Erreur parsing {os.path.basename(xml_path)}: {e}", Qgis.Warning)
        except Exception as e:
            self.log_message(f"Erreur traitement {os.path.basename(xml_path)}: {e}", Qgis.Warning)

        return descriptions_data

    def create_temp_layer(self, descriptions_data: list) -> QgsVectorLayer:
        fields = [
            QgsField('NM_SFFZN', QVariant.String),
            QgsField('VOLET_ZNIEFF', QVariant.String),
            QgsField('TERRITOIRE', QVariant.String),
            QgsField('NM_SFFZN_PARENT', QVariant.String),
            QgsField('NM_REGZN', QVariant.String),
            QgsField('LB_ZN', QVariant.String),
            QgsField('TY_ZONE', QVariant.String),
            QgsField('SU_ZN', QVariant.Double),
            QgsField('PROF_MINI', QVariant.Double),
            QgsField('PROF_MAXI', QVariant.Double),
            QgsField('ALT_MINI', QVariant.Double),
            QgsField('ALT_MAXI', QVariant.Double),
            QgsField('X_L2E', QVariant.Double),
            QgsField('Y_L2E', QVariant.Double),
            QgsField('FG_EVOL', QVariant.String),
            QgsField('FG_EVOL_ANC', QVariant.String),
            QgsField('FG_CONTOUR', QVariant.String),
            QgsField('TX_GEO', QVariant.String),
            QgsField('TX_ACTH', QVariant.String),
            QgsField('TX_MESPRO', QVariant.String),
            QgsField('TX_HYDRO', QVariant.String),
            QgsField('TX_GRANULO', QVariant.String),
            QgsField('TX_INTERET', QVariant.String),
            QgsField('TX_FACT', QVariant.String),
            QgsField('DESCRIPTION', QVariant.String),
            QgsField('TX_DELIM', QVariant.String),
            QgsField('TX_TYPO', QVariant.String),
            QgsField('FG_SUPP', QVariant.String),
            QgsField('DATE_CREA', QVariant.String),
            QgsField('DATE_MODIF', QVariant.String),
            QgsField('TYPE1_INCLU', QVariant.String),
            QgsField('INCLU_DANS_TYPE2', QVariant.String),
            QgsField('ZNI_ID_ZNIEFF', QVariant.String),
            QgsField('ZNI_NM_SFFZN', QVariant.String),
            QgsField('ZNI_LB_ZN', QVariant.String),
            QgsField('ZNI_TY_ZONE', QVariant.String),
            QgsField('ZNI_NM_REGZN', QVariant.String),
            QgsField('ZNI_VOLET_ZNIEFF', QVariant.String),
            QgsField('HTML_POPUP', QVariant.String),
        ]

        layer = QgsVectorLayer("None", f"{self.get_layer_name()}_temp", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        layer.setDisplayExpression("coalesce(LB_ZN, '') || ' (' || coalesce(NM_SFFZN, '') || ')'")

        numeric_fields = {'SU_ZN', 'PROF_MINI', 'PROF_MAXI', 'ALT_MINI', 'ALT_MAXI', 'X_L2E', 'Y_L2E'}
        success_count = 0
        error_count = 0

        for i, data in enumerate(descriptions_data, 1):
            try:
                feat = QgsFeature()
                feat.setFields(layer.fields())
                attrs = []
                for f in layer.fields():
                    val = data.get(f.name(), '')
                    attrs.append(self._to_double(val) if f.name() in numeric_fields else val)
                feat.setAttributes(attrs)

                if provider.addFeature(feat):
                    success_count += 1
                else:
                    error_count += 1
                    self.log_message(f"Échec ajout feature {i}", Qgis.Warning)

            except Exception as e:
                error_count += 1
                self.log_message(f"Erreur feature {i}: {e}", Qgis.Warning)

        layer.updateExtents()
        level = Qgis.Success if error_count == 0 else Qgis.Warning
        self.log_message(
            f"Couche créée : {success_count} entrées, {error_count} erreurs", level
        )
        return layer

    def load_from_geopackage(self):
        """Surcharge : applique setDisplayExpression après chargement."""
        layer_name = self.get_layer_name()
        try:
            uri = f"{self.gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, layer_name, "ogr")
            if layer.isValid():
                layer.setDisplayExpression(
                    "coalesce(LB_ZN, '') || ' (' || coalesce(NM_SFFZN, '') || ')'"
                )
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
        """Retourne le texte d'un élément XML simple, ou une chaîne vide."""
        if element is not None and element.text:
            return element.text.strip()
        return ""

    def _rich_text(self, element) -> str:
        """Extrait le texte d'un élément pouvant contenir des balises <p>."""
        if element is None:
            return ""
        if element.text and element.text.strip():
            text = element.text.strip()
        else:
            paragraphs = [p.text.strip() for p in element.findall('.//p') if p.text]
            text = '\n'.join(paragraphs) if paragraphs else ''.join(element.itertext()).strip()
        return ' '.join(text.split()) if text else ""

    def _extract_zni(self, znieff_elem) -> dict:
        """Extrait les données ZNI imbriquées."""
        zni_data = {}
        zni_elem = znieff_elem.find('ZNI')
        if zni_elem is not None:
            row = zni_elem.find('ZNI_ROW')
            if row is not None:
                for key in ('ID_ZNIEFF', 'NM_SFFZN', 'LB_ZN', 'TY_ZONE', 'NM_REGZN', 'VOLET_ZNIEFF'):
                    zni_data[key] = self._text(row.find(key))
        return zni_data

    def _to_double(self, value):
        """Convertit une valeur en float, retourne None si impossible."""
        if not value:
            return None
        try:
            cleaned = ''.join(c for c in str(value).replace(',', '.').strip() if c.isdigit() or c in '.-')
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    def _html_popup(self, nm_sffzn: str, lb_zn: str, description: str) -> str:
        """Génère le HTML de popup QGIS pour une description ZNIEFF."""
        safe_num = html.escape(nm_sffzn) if nm_sffzn else "Non renseigné"
        safe_name = html.escape(lb_zn) if lb_zn else "Non renseigné"
        if description:
            safe_desc = html.escape(description).replace('  ', ' ').replace('\n', '<br>')
        else:
            safe_desc = '<i>Aucune description disponible</i>'

        return f"""<!DOCTYPE html>
<html>
<head><style>
  body {{ font-family: Arial, sans-serif; margin: 10px; }}
  .header {{ color: #009999; border-bottom: 2px solid #009999; padding-bottom: 5px; margin-bottom: 15px; }}
  .title {{ font-size: 16px; font-weight: bold; }}
  .subtitle {{ font-size: 14px; color: #666; }}
  .section-title {{ font-weight: bold; color: #009999; margin-bottom: 5px; }}
  .content {{ margin-left: 10px; text-align: justify; line-height: 1.5; }}
</style></head>
<body>
  <div class="header">
    <div class="title">{safe_name}</div>
    <div class="subtitle">ZNIEFF : {safe_num}</div>
  </div>
  <div><div class="section-title">Description :</div>
    <div class="content">{safe_desc}</div>
  </div>
</body></html>"""


def run_module_with_path(folder_path: str):
    return ZnieffXmlToLayerDesc().run_with_path(folder_path)


if __name__ == "__console__":
    ZnieffXmlToLayerDesc().run()
