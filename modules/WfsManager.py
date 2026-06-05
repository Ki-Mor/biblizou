# -*- coding: utf-8 -*-
from qgis.utils import iface
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsProject, QgsVectorLayer, QgsMessageLog, Qgis

def setup_wfs_connections():
    """Ajoute les connexions WFS dans le registre QGIS"""
    try:
        s = QSettings()
        # Connexion IGN
        # s.setValue("qgis/connections-wfs/IGN - Services WFS/url", "https://data.geopf.fr/wfs/ows?VERSION=2.0.0")
        # Connexion INPN
        s.setValue("qgis/connections-wfs/INPN - Services WFS/url", "https://data.geopf.fr/annexes/mnhn/capabilities/patrinat_wfs")
        if iface:
            iface.reloadConnections()
        return True, "Connexions configurées"
    except Exception as e:
        return False, str(e)

def load_wfs_layers():
    """Charge les couches dans le projet"""
    layers = [
        ('Patrinat : ZPS', 'https://data.geopf.fr/annexes/mnhn/capabilities/patrinat_wfs', 'patrinat_zps:zps', 'EPSG:3857'),
        ('Patrinat : SIC', 'https://data.geopf.fr/annexes/mnhn/capabilities/patrinat_wfs', 'patrinat_sic:sic', 'EPSG:3857'),
        ('Patrinat : ZNIEFF1', 'https://data.geopf.fr/annexes/mnhn/capabilities/patrinat_wfs', 'patrinat_znieff1:znieff1', 'EPSG:3857'),
        ('Patrinat : ZNIEFF2', 'https://data.geopf.fr/annexes/mnhn/capabilities/patrinat_wfs', 'patrinat_znieff2:znieff2', 'EPSG:3857'),

        # ('ADMIN EXPRESS - Dept', 'https://data.geopf.fr/wfs/ows', 'LIMITES_ADMINISTRATIVES_EXPRESS.LATEST:departement', 'EPSG:4326')
    ]
    for name, url, dtype, srs in layers:
        if not QgsProject.instance().mapLayersByName(name):
            uri = f"restrictToRequestBBOX='1' srsname='{srs}' typename='{dtype}' url='{url}' version='auto'"
            vlayer = QgsVectorLayer(uri, name, "WFS")
            if vlayer.isValid():
                QgsProject.instance().addMapLayer(vlayer)
    return True, "Couches importées"