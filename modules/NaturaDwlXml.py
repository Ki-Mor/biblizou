# -*- coding: utf-8 -*-
"""
Auteur : François Botcazou
Nom : NaturaDwlXml.py
Groupe : FSD
Description : Module pour télécharger les xml des zonages Natura dans un périmètre donné.
"""

from .base.DwlXml import DwlXml


class NaturaDwlXml(DwlXml):
    """
    Téléchargement des FSD Natura 2000 (SIC + ZPS) depuis l'INPN.

    Implémente les 2 méthodes abstraites de DwlXml :
        - get_patrinat_layer_names() → ('Patrinat : SIC', 'Patrinat : ZPS')
        - build_url()                → URL fsdxml INPN
    """

    def get_patrinat_layer_names(self) -> tuple:
        return ('Patrinat : SIC', 'Patrinat : ZPS')

    def build_url(self, zone_id: str) -> str:
        return f"https://inpn.mnhn.fr/docs/natura2000/fsdxml/{zone_id}.xml"


def run_module_with_path(reference_layer, folder_path: str) -> bool:
    return NaturaDwlXml().run_with_path(reference_layer, folder_path)


if __name__ == "__console__":
    pass
