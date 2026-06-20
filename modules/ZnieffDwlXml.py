# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : ZnieffDwlXml.py
Groupe : FSD
Description : Module pour télécharger les xml des zonages ZNIEFF dans un périmètre donné.
"""

from .base.DwlXml import DwlXml


class ZnieffDwlXml(DwlXml):
    """
    Téléchargement des fiches ZNIEFF (ZN1 + ZN2) depuis l'INPN.

    Implémente les 2 méthodes abstraites de DwlXml :
        - get_patrinat_layer_names() → ('Patrinat : ZNIEFF1', 'Patrinat : ZNIEFF2')
        - build_url()                → URL znieffxml INPN
    """

    def get_patrinat_layer_names(self) -> tuple:
        return ('Patrinat : ZNIEFF1', 'Patrinat : ZNIEFF2')

    def build_url(self, zone_id: str) -> str:
        return f"https://inpn.mnhn.fr/docs/ZNIEFF/znieffxml/{zone_id}.xml"


def run_module_with_path(reference_layer, folder_path: str) -> bool:
    return ZnieffDwlXml().run_with_path(reference_layer, folder_path)


if __name__ == "__console__":
    pass
